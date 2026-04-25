// src/components/Alerta.tsx
import { useState, useEffect } from "react";
import { Carousel } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faExclamationTriangle,
  faTimes,
  faBell,
  faChevronLeft,
  faChevronRight,
  faCalendarAlt,
} from "@fortawesome/free-solid-svg-icons";
import type { ContenidoData } from "../data/mockData";

interface AlertaProps {
  contenidos: ContenidoData[];
}
export function Alerta({ contenidos }: AlertaProps) {
  const [showFullscreen, setShowFullscreen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  // Filtramos solo los contenidos que son tipo ALERTA
  const alertasActivas = contenidos.filter(
    (c) => c.tipo_contenido === "ALERTA",
  );

  const cantidadAlertas = alertasActivas.length;

  // CÁLCULO DE TIEMPOS: 30s si es 1 alerta, 15s por alerta si son varias.
  const tiempoTotalCalculado = cantidadAlertas > 1 ? cantidadAlertas * 15 : 30;
  const intervaloCarrusel = cantidadAlertas > 1 ? 15000 : undefined; // 15 segs

  const [timeLeft, setTimeLeft] = useState(tiempoTotalCalculado);

  // 1. Mostrar automáticamente al cargar si hay alertas
  useEffect(() => {
    if (cantidadAlertas > 0) {
      setShowFullscreen(true);
    }
  }, [cantidadAlertas]);

  // 2. Lógica del Cronómetro Global
  useEffect(() => {
    let timer: number;
    if (showFullscreen && timeLeft > 0) {
      timer = window.setInterval(() => {
        setTimeLeft((prev) => prev - 1);
      }, 1000);
    } else if (timeLeft === 0) {
      handleMinimize();
    }
    return () => clearInterval(timer);
  }, [showFullscreen, timeLeft]);

  const handleMinimize = () => {
    setShowFullscreen(false);
    setMinimized(true);
  };

  const handleReopen = () => {
    setMinimized(false);
    setShowFullscreen(true);
    setTimeLeft(tiempoTotalCalculado); // Reiniciamos el tiempo total
    setActiveIndex(0); // Volvemos a la primera alerta
  };

  const handleSelect = (selectedIndex: number) => {
    setActiveIndex(selectedIndex);
  };

  const handlePrev = () => {
    setActiveIndex((prev) => (prev === 0 ? cantidadAlertas - 1 : prev - 1));
  };

  const handleNext = () => {
    setActiveIndex((prev) => (prev === cantidadAlertas - 1 ? 0 : prev + 1));
  };

  if (cantidadAlertas === 0) return null;

  return (
    <>
      {/* OVERLAY DE PANTALLA COMPLETA ESTILO FIGMA */}
      {showFullscreen && (
        <div
          className="fixed-top w-100 h-100 d-flex flex-column align-items-center justify-content-center p-4"
          style={{
            zIndex: 9999,
            backgroundColor: "rgba(15, 20, 15, 0.95)", // Fondo oscuro
            backgroundImage:
              "repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.2) 10px, rgba(0,0,0,0.2) 20px)",
            backdropFilter: "blur(8px)",
          }}
        >
          {/* CONTENEDOR PRINCIPAL */}
          <div className="w-100" style={{ maxWidth: "1000px" }}>
            {/* BARRA SUPERIOR DE CONTROLES */}
            <div className="d-flex justify-content-between align-items-center mb-3 w-100">
              <div>
                {cantidadAlertas > 1 && (
                  <div className="d-flex align-items-center gap-2">
                    <button
                      className="btn btn-dark border-secondary rounded-3 d-flex justify-content-center align-items-center"
                      style={{ width: "40px", height: "40px" }}
                      onClick={handlePrev}
                    >
                      <FontAwesomeIcon icon={faChevronLeft} />
                    </button>
                    <span
                      className="badge bg-dark border border-secondary text-light fs-6 px-3 py-2 rounded-3"
                      style={{ minWidth: "60px" }}
                    >
                      {activeIndex + 1} / {cantidadAlertas}
                    </span>
                    <button
                      className="btn btn-dark border-secondary rounded-3 d-flex justify-content-center align-items-center"
                      style={{ width: "40px", height: "40px" }}
                      onClick={handleNext}
                    >
                      <FontAwesomeIcon icon={faChevronRight} />
                    </button>
                  </div>
                )}
              </div>

              <div className="d-flex align-items-center gap-3">
                <div
                  className="rounded-circle border border-secondary bg-dark text-white d-flex justify-content-center align-items-center fw-bold shadow"
                  style={{ width: "50px", height: "50px", fontSize: "1.2rem" }}
                >
                  {timeLeft}
                </div>
                <button
                  className="btn btn-dark border-secondary rounded-3 d-flex justify-content-center align-items-center shadow"
                  style={{ width: "50px", height: "50px", fontSize: "1.2rem" }}
                  onClick={handleMinimize}
                >
                  <FontAwesomeIcon icon={faTimes} />
                </button>
              </div>
            </div>

            {/* CARRUSEL DE ALERTAS */}
            <Carousel
              activeIndex={activeIndex}
              onSelect={handleSelect}
              indicators={cantidadAlertas > 1}
              controls={false}
              interval={intervaloCarrusel}
              className="shadow-lg rounded-4 overflow-hidden"
              slide={false}
              fade={true}
            >
              {alertasActivas.map((alerta) => {
                const tieneImagen =
                  alerta.imagen_url && alerta.imagen_url.trim() !== "";

                return (
                  <Carousel.Item key={alerta.id}>
                    {tieneImagen ? (
                      /* =========================================================
                         DISEÑO 1: CON IMAGEN (Dividido) 
                         ========================================================= */
                      <div
                        className="d-flex flex-column flex-md-row bg-success"
                        style={{
                          minHeight: "450px",
                          backgroundColor: "#007b33",
                        }}
                      >
                        {/* LADO IZQUIERDO: IMAGEN */}
                        <div
                          className="w-100 w-md-50 d-none d-sm-block"
                          style={{
                            backgroundImage: `url(${alerta.imagen_url})`,
                            backgroundSize: "cover",
                            backgroundPosition: "center",
                          }}
                        />

                        {/* LADO DERECHO: CONTENIDO */}
                        <div
                          className="w-100 w-md-50 p-4 p-md-5 text-white d-flex flex-column position-relative"
                          style={{ backgroundColor: "#1e824c" }}
                        >
                          <div
                            className="position-absolute top-0 end-0 m-4 rounded-circle border border-2 border-white d-flex justify-content-center align-items-center opacity-75"
                            style={{
                              width: "55px",
                              height: "55px",
                              animation: "ondas-pulsantes-blancas 2s infinite",
                            }}
                          >
                            <FontAwesomeIcon
                              icon={faExclamationTriangle}
                              className="fs-3"
                            />
                          </div>

                          <h1
                            className="fw-black mb-4 mt-2 pe-5"
                            style={{ fontSize: "2.5rem", lineHeight: "1.1" }}
                          >
                            {alerta.titulo}
                          </h1>
                          <p className="fs-5 mb-5" style={{ opacity: 0.9 }}>
                            {alerta.contenido}
                          </p>

                          <div className="d-flex flex-wrap gap-2 mt-auto">
                            {/**Fecha Publicada de Contenidos*/}
                            <span
                              className="badge rounded-pill border border-light text-light px-3 py-2 fw-normal"
                              style={{
                                backgroundColor: "rgba(255,255,255,0.15)",
                              }}
                            >
                              <FontAwesomeIcon
                                icon={faCalendarAlt}
                                className="me-2 text-info"
                              />
                              8 Abr 2026 - 13:45 hrs
                            </span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* =========================================================
                         DISEÑO 2: SIN IMAGEN (Centrado) 
                         ========================================================= */
                      <div
                        className="d-flex flex-column align-items-center justify-content-center text-center p-5 text-white"
                        style={{
                          minHeight: "450px",
                          backgroundColor: "#1e824c",
                        }}
                      >
                        {/* Etiqueta Superior de Emergencia */}
                        <div
                          className="badge rounded-pill border border-warning text-warning px-4 py-2 mb-4 d-flex align-items-center gap-2"
                          style={{
                            backgroundColor: "rgba(255,193,7,0.1)",
                            fontSize: "1rem",
                          }}
                        >
                          <FontAwesomeIcon icon={faExclamationTriangle} />
                          EMERGENCIA
                        </div>

                        {/* Título Principal Centrado */}
                        <h1
                          className="fw-black mb-4 w-100"
                          style={{
                            fontSize: "3rem",
                            lineHeight: "1.2",
                            maxWidth: "800px",
                          }}
                        >
                          {alerta.titulo}
                        </h1>

                        {/* Descripción Centrada */}
                        <p
                          className="fs-4 mb-5"
                          style={{ opacity: 0.9, maxWidth: "750px" }}
                        >
                          {alerta.contenido}
                        </p>

                        {/* Etiquetas inferiores centradas */}
                        <div className="d-flex justify-content-center flex-wrap gap-3 mt-4">
                          <span
                            //Fecha Publicada de Contenidos
                            className="badge rounded-pill border border-light text-light px-3 py-2 fw-normal fs-6"
                            style={{
                              backgroundColor: "rgba(255,255,255,0.15)",
                            }}
                          >
                            <FontAwesomeIcon
                              icon={faCalendarAlt}
                              className="me-2 text-info"
                            />
                            8 Abr 2026 - 13:45 hrs
                          </span>
                        </div>
                      </div>
                    )}
                  </Carousel.Item>
                );
              })}
            </Carousel>
          </div>
        </div>
      )}

      {/* BOTÓN FLOTANTE CIRCULAR CON ONDAS ROJAS (MINIMIZADO) */}
      {minimized && (
        <div
          className="position-fixed bottom-0 end-0 m-4"
          style={{ zIndex: 9000 }}
        >
          <button
            className="btn btn-danger rounded-circle d-flex align-items-center justify-content-center p-0 border-0"
            onClick={handleReopen}
            style={{
              width: "100px",
              height: "100px",
              animation: "ondas-pulsantes-rojas 2.5s infinite",
              boxShadow: "none",
            }}
          >
            <FontAwesomeIcon icon={faBell} style={{ fontSize: "2.5rem" }} />
            <span
              className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-warning text-dark border border-white"
              style={{ fontSize: "1.5rem" }}
            >
              {cantidadAlertas}
            </span>
          </button>
        </div>
      )}

      {/* ESTILOS CSS */}
      <style>{`
        @keyframes ondas-pulsantes-rojas {
          0% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7), 0 0 0 0 rgba(220, 53, 69, 0.7); }
          40% { box-shadow: 0 0 0 20px rgba(220, 53, 69, 0), 0 0 0 0 rgba(220, 53, 69, 0.7); }
          80% { box-shadow: 0 0 0 40px rgba(220, 53, 69, 0), 0 0 0 20px rgba(220, 53, 69, 0); }
          100% { box-shadow: 0 0 0 40px rgba(220, 53, 69, 0), 0 0 0 40px rgba(220, 53, 69, 0); }
        }

        @keyframes ondas-pulsantes-blancas {
          0% { box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.6), 0 0 0 0 rgba(255, 255, 255, 0.6); }
          40% { box-shadow: 0 0 0 15px rgba(255, 255, 255, 0), 0 0 0 0 rgba(255, 255, 255, 0.6); }
          80% { box-shadow: 0 0 0 30px rgba(255, 255, 255, 0), 0 0 0 15px rgba(255, 255, 255, 0); }
          100% { box-shadow: 0 0 0 30px rgba(255, 255, 255, 0), 0 0 0 30px rgba(255, 255, 255, 0); }
        }
      `}</style>
    </>
  );
}
