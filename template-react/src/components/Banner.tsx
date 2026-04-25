// src/components/Banner.tsx
import { Carousel, Button } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faImage } from "@fortawesome/free-solid-svg-icons";
import type { ContenidoData } from "../data/mockData";
interface BannerProps {
  contenidos: ContenidoData[]; //
  onAbrirDetalles: (contenido: ContenidoData) => void;
}

export function Banner({ onAbrirDetalles, contenidos }: BannerProps) {
  const banners = contenidos.filter((c) => c.tipo_contenido === "BANNER");

  return (
    <div className="container-fluid mt-4 mb-5">
      <Carousel
        className="shadow-lg rounded overflow-hidden"
        slide={false}
        fade
      >
        {banners.map((banner) => (
          <Carousel.Item
            key={banner.id}
            style={{
              height: "500px", // ALTO ESTÁTICO FIJO
              backgroundColor: banner.color,
            }}
          >
            <div className="d-flex w-100 h-100">
              {/* --- LADO IZQUIERDO: Cuadro de la Imagen --- */}
              <div
                className="d-flex justify-content-center align-items-center"
                style={{
                  width: "40%", // Ancho estático
                  paddingLeft: "10%", // Zona segura para la flecha izquierda
                  paddingRight: "5%", // Respiro para separarlo del texto
                }}
              >
                {/* Contenedor Opaco/Borroso de la imagen */}
                <div
                  className="p-2 rounded-4 shadow-lg d-flex align-items-center justify-content-center"
                  style={{
                    width: "100%",
                    height: "280px", // Alto estático
                    background: "rgba(255,255,255,0.15)",
                    backdropFilter: "blur(8px)",
                    border: "1px solid rgba(255,255,255,0.3)",
                  }}
                >
                  {banner.imagen_url ? (
                    <img
                      src={banner.imagen_url}
                      alt={banner.titulo}
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        borderRadius: "12px",
                      }}
                    />
                  ) : (
                    <div className="text-white opacity-50 display-1">
                      <FontAwesomeIcon icon={faImage} />
                    </div>
                  )}
                </div>
              </div>

              {/* --- LADO DERECHO: Contenido (Textos y Botón) --- */}
              <div
                className="d-flex flex-column justify-content-center text-white"
                style={{
                  width: "60%", // Ancho estático
                  paddingLeft: "5%", // Respiro para separarlo de la imagen
                  paddingRight: "10%", // Zona segura para la flecha derecha
                }}
              >
                <div className="mb-2">
                  <span
                    className="badge rounded-pill text-uppercase tracking-wider fw-bold"
                    style={{
                      backgroundColor: "rgba(255,255,255,0.2)",
                      padding: "6px 12px",
                    }}
                  >
                    Destacado
                  </span>
                </div>

                <h1 className="fw-bold text-shadow">{banner.titulo}</h1>

                <h4
                  className="mt-2"
                  style={{
                    display: "-webkit-box",
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {banner.contenido}
                </h4>

                <div>
                  <Button
                    variant="light"
                    className="fw-bold shadow mt-2 px-4 py-3 ptext-dark position-relative"
                    style={{ zIndex: 10 }} // Asegura el clic por encima de la flecha
                    onClick={() => onAbrirDetalles(banner)}
                  >
                    Ver Detalles
                  </Button>
                </div>
              </div>
            </div>
          </Carousel.Item>
        ))}
      </Carousel>
    </div>
  );
}
