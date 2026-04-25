// src/components/GrillaCards.tsx
import { Card } from "react-bootstrap";
import { useRef, useState, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faHeart,
  faInfoCircle,
  faBell,
  faNewspaper,
  faThumbtack,
} from "@fortawesome/free-solid-svg-icons";
import type { ContenidoData } from "../data/mockData";

interface GrillaCardsProps {
  onAbrirDetalles: (contenido: ContenidoData) => void;
  contenidos: ContenidoData[];
}

const obtenerIcono = (tipo: string) => {
  switch (tipo) {
    case "EVENTO":
      return <FontAwesomeIcon icon={faHeart} className="text-secondary" />;
    case "INFORMACION":
      return <FontAwesomeIcon icon={faInfoCircle} className="text-secondary" />;
    case "AVISO":
      return <FontAwesomeIcon icon={faBell} className="text-secondary" />;
    case "NOTICIA":
      return <FontAwesomeIcon icon={faNewspaper} className="text-secondary" />;
    default:
      return <FontAwesomeIcon icon={faThumbtack} className="text-secondary" />;
  }
};

export function GrillaCards({ onAbrirDetalles, contenidos }: GrillaCardsProps) {
  const scrollContainer = useRef<HTMLDivElement>(null);

  // ESTADO: Guardamos cuántas columnas deben verse según la pantalla
  const [columnasVisibles, setColumnasVisibles] = useState(3);

  // EFECTO: Escucha el tamaño de la ventana (Responsividad)
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width < 768) {
        setColumnasVisibles(1); // Celulares: 1 columna
      } else if (width < 1024) {
        setColumnasVisibles(2); // Tablets: 2 columnas
      } else {
        setColumnasVisibles(3); // Monitores: 3 columnas
      }
    };

    handleResize(); // Se ejecuta al cargar
    window.addEventListener("resize", handleResize); // Se ejecuta al redimensionar
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const cardsParaMostrar = contenidos.filter(
    (c) => c.tipo_contenido !== "BANNER" && c.tipo_contenido !== "ALERTA",
  );

  const scroll = (direction: "left" | "right") => {
    if (scrollContainer.current) {
      const scrollAmount = scrollContainer.current.clientWidth + 20; // + 20 del gap

      scrollContainer.current.scrollBy({
        left: direction === "left" ? -scrollAmount : scrollAmount,
        behavior: "smooth",
      });
    }
  };

  // CÁLCULO MATEMÁTICO DEL ANCHO
  const gapSize = 20;
  const anchoCalculado =
    columnasVisibles === 1
      ? "100%" // Si es móvil, ocupa todo el ancho
      : `calc((100% - ${(columnasVisibles - 1) * gapSize}px) / ${columnasVisibles})`; // Fórmula para 2 o 3 columnas

  return (
    <div className="container mt-4 mb-5">
      <div className="d-flex align-items-center gap-3">
        {/* Botón Izquierdo */}
        <button
          onClick={() => scroll("left")}
          className="btn btn-outline-success d-none d-md-block"
          style={{ minWidth: "40px" }}
        >
          ◀
        </button>

        <div
          ref={scrollContainer}
          style={{
            display: "grid",
            gridTemplateRows: "repeat(2, 1fr)",
            gridAutoFlow: "column",
            gridAutoColumns: anchoCalculado,
            gap: `${gapSize}px`,
            paddingBottom: "15px",
            overflowX: "auto",
            flex: 1,
            scrollSnapType: "x mandatory",
            scrollbarWidth: "none",
            msOverflowStyle: "none",
          }}
        >
          {cardsParaMostrar.map((card) => (
            <Card
              key={card.id}
              className="border-success shadow-sm"
              style={{
                backgroundColor: card.color || "#D0F0C0", // <--- ¡AQUÍ ESTÁ EL CAMBIO!
                cursor: "pointer",
                minHeight: "140px",
                scrollSnapAlign: "start",
              }}
              onClick={() => onAbrirDetalles(card)}
            >
              <Card.Body className="d-flex justify-content-between align-items-center p-4">
                <h4 className="mb-0 fw-bold text-dark" style={{ width: "75%" }}>
                  {card.titulo}
                </h4>
                <div
                  className="d-flex justify-content-center align-items-center rounded-circle shadow-sm flex-shrink-0"
                  style={{
                    width: "60px",
                    height: "60px",
                    backgroundColor: "#ffffff", // Fondo blanco para que el ícono destaque más sobre el verde claro
                    fontSize: "1.6rem",
                  }}
                >
                  {obtenerIcono(card.tipo_contenido)}
                </div>
              </Card.Body>
            </Card>
          ))}
        </div>

        {/* Botón Derecho */}
        <button
          onClick={() => scroll("right")}
          className="btn btn-outline-success d-none d-md-block"
          style={{ minWidth: "40px" }}
        >
          ▶
        </button>
      </div>

      {/* CSS extra para ocultar la barra en navegadores webkit */}
      <style>{`
        div::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
}
