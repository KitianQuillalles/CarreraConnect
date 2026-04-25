// src/components/ModalDetalle.tsx
import { Modal, Button } from "react-bootstrap";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faFilePdf,
  faImage,
  faFileAlt,
} from "@fortawesome/free-solid-svg-icons";
import type { ContenidoData } from "../data/mockData";

interface ModalDetalleProps {
  show: boolean;
  onHide: () => void;
  contenido: ContenidoData | null;
}

export function ModalDetalle({ show, onHide, contenido }: ModalDetalleProps) {
  if (!contenido) return null;

  const esImagen = (url: string) => /\.(jpg|jpeg|png|gif|webp)$/i.test(url);
  const esPdf = (url: string) => /\.pdf$/i.test(url);

  return (
    <Modal
      show={show}
      onHide={onHide}
      size="lg"
      centered
      scrollable
      animation={false}
    >
      <Modal.Header
        closeButton
        style={{
          backgroundColor: contenido.color || "#005c3c",
          color: "white",
        }}
        closeVariant="white"
      >
        <Modal.Title className="fw-bold fs-5">
          {contenido.tipo_contenido}
        </Modal.Title>
      </Modal.Header>

      <Modal.Body className="p-0">
        <div className="p-4">
          <h2 className="fw-bold mb-3">{contenido.titulo}</h2>

          <p
            style={{
              whiteSpace: "pre-wrap",
              fontSize: "1.1rem",
              color: "#444",
            }}
          >
            {contenido.contenido}
          </p>

          {contenido.archivos && contenido.archivos.length > 0 && (
            <div className="mt-5">
              <h5 className="fw-bold border-bottom pb-2 mb-3">
                Archivos Adjuntos
              </h5>

              <div className="d-flex flex-column gap-4">
                {contenido.archivos.map((archivo) => {
                  const isImg = esImagen(archivo.url);
                  const isPdf = esPdf(archivo.url);

                  return (
                    <div
                      key={archivo.id}
                      className="border rounded p-3 bg-light shadow-sm"
                    >
                      <div className="mb-3">
                        <p className="mb-0 fw-bold text-secondary text-truncate">
                          <FontAwesomeIcon
                            icon={
                              isPdf ? faFilePdf : isImg ? faImage : faFileAlt
                            }
                            className="me-2"
                          />
                          Anexo: {archivo.nombre}
                        </p>
                        {/* EL BOTÓN "ABRIR / DESCARGAR" HA SIDO ELIMINADO DE AQUÍ */}
                      </div>

                      {isImg ? (
                        <div className="text-center bg-white border rounded p-2 mt-2">
                          <img
                            src={archivo.url}
                            alt={archivo.nombre}
                            className="img-fluid rounded"
                            style={{
                              maxHeight: "450px",
                              display: "block",
                              margin: "0 auto",
                              objectFit: "contain",
                            }}
                          />
                        </div>
                      ) : isPdf ? (
                        <div className="ratio ratio-16x9">
                          <iframe
                            src={archivo.url}
                            className="border rounded"
                            title={archivo.nombre}
                          />
                        </div>
                      ) : (
                        <div className="text-center p-3 bg-white border rounded text-muted">
                          Vista previa no disponible para este formato.
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </Modal.Body>

      <Modal.Footer className="bg-light">
        <Button variant="secondary" onClick={onHide}>
          Cerrar
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
