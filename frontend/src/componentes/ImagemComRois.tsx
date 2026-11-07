import { useEffect, useState } from "react";
import type { Roi } from "../tipos/diagnostico";

async function paraDataUrl(imagem: Blob): Promise<string> {
  const bytes = new Uint8Array(await imagem.arrayBuffer());
  let binario = "";
  // Em blocos: String.fromCharCode com milhões de argumentos estoura a pilha.
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binario += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return `data:${imagem.type || "image/jpeg"};base64,${btoa(binario)}`;
}

/**
 * Imagem com as ROIs por cima. As coordenadas são pixels da imagem original (011 §5.2), então o
 * desenho usa o tamanho natural da imagem como sistema de coordenadas e escala junto com ela.
 */
export function ImagemComRois({
  imagem,
  rois = [],
  descricao,
}: {
  imagem: Blob;
  rois?: Roi[];
  descricao: string;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [tamanho, setTamanho] = useState<{ w: number; h: number } | null>(null);

  useEffect(() => {
    // Data URL em vez de object URL: nada a revogar, e o StrictMode não quebra a imagem.
    let vivo = true;
    void paraDataUrl(imagem).then((u) => {
      if (vivo) setUrl(u);
    });
    return () => {
      vivo = false;
    };
  }, [imagem]);

  if (!url) return null;
  // w-fit e self-start: a figura tem a largura da imagem; senão o SVG estica no flex e as ROIs saem da escala.
  return (
    <figure className="relative w-fit max-w-full self-start">
      <img
        src={url}
        alt={descricao}
        className="block max-w-full"
        onLoad={(e) => {
          setTamanho({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight });
        }}
      />
      {tamanho && rois.length > 0 && (
        <svg
          viewBox={`0 0 ${String(tamanho.w)} ${String(tamanho.h)}`}
          preserveAspectRatio="none"
          className="pointer-events-none absolute inset-0 size-full"
          aria-hidden="true"
        >
          {rois.map((r, i) => (
            <g key={i}>
              <rect
                x={r.x}
                y={r.y}
                width={r.largura}
                height={r.altura}
                className="fill-none stroke-amarelo"
                strokeWidth="3"
                vectorEffect="non-scaling-stroke"
                data-roi={i + 1}
              />
              <text
                x={r.x}
                y={Math.max(r.y - 4, 12)}
                className="fill-amarelo stroke-tinta font-bold"
                strokeWidth="0.6"
                fontSize={Math.max(14, tamanho.h / 30)}
              >
                {i + 1}
              </text>
            </g>
          ))}
        </svg>
      )}
    </figure>
  );
}
