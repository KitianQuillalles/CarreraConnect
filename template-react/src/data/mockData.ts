// src/data/mockData.ts

export interface ArchivoData {
  id: number;
  nombre: string;
  url: string;
}

export interface ContenidoData {
  id: number;
  titulo: string;
  contenido: string;
  imagen_url: string;
  color: string;
  es_vertical: boolean;
  tipo_contenido:
    | "NOTICIA"
    | "INFORMACION"
    | "AVISO"
    | "OTRO"
    | "BANNER"
    | "ALERTA"
    | "EVENTO";
  archivos?: ArchivoData[];
}

export const contenidosFalsos: ContenidoData[] = [
  // --- ALERTAS (CON Y SIN IMAGEN) ---
  {
    id: 18,
    titulo: "Suspensión de Clases por Corte de Agua",
    contenido:
      "Se suspenden todas las actividades académicas hoy 8 de abril desde las 14:00 hrs debido a corte de suministro de agua. Las clases se retomarán mañana en horario normal.",
    imagen_url: "", // SIN IMAGEN (Diseño Centrado)
    color: "#d32f2f",
    es_vertical: false,
    tipo_contenido: "ALERTA",
  },
  {
    id: 19,
    titulo: "Cambio en Horario de Atención Cafetería",
    contenido:
      "A partir de esta semana, la cafetería abrirá una hora después. Nuevo horario: 8:00 AM.",
    imagen_url: "", // SIN IMAGEN (Diseño Centrado)
    color: "#d32f2f",
    es_vertical: false,
    tipo_contenido: "ALERTA",
  },
  {
    id: 20,
    titulo: "Corte de Energía Programado",
    contenido:
      "Se realizará mantenimiento eléctrico en el sector norte del campus el próximo sábado. Posibles interrupciones de servicio en laboratorios.",
    // CON IMAGEN (Diseño Dividido)
    imagen_url:
      "https://images.unsplash.com/photo-1544725121-be3bf52e2dc8?q=80&w=1000&auto=format&fit=crop",
    color: "#d32f2f",
    es_vertical: false,
    tipo_contenido: "ALERTA",
  },
  // --- AVISOS ---
  {
    id: 8,
    titulo: "Movilidad Estudiantil Internacional",
    contenido:
      "Conoce los convenios de intercambio disponibles para el próximo año.",
    imagen_url:
      "https://images.unsplash.com/photo-1523580494863-6f3031224c94?q=80&w=500&auto=format&fit=crop",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "AVISO",
  },
  {
    id: 12,
    titulo: "Convocatoria Monitores Académicos",
    contenido:
      "Se buscan estudiantes destacados para ejercer como monitores en laboratorios.",
    imagen_url:
      "https://images.unsplash.com/photo-1552664730-d307ca884978?q=80&w=500&auto=format&fit=crop",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "AVISO",
  },
  // --- BANNERS ---
  {
    id: 1,
    titulo: "XIII Torneo Nacional de Debates",
    contenido:
      "Participa en las clasificatorias Santo Tomás 2025. Un espacio para desarrollar tus habilidades.",
    imagen_url:
      "https://images.unsplash.com/photo-1541829070764-84a7d30dd3f3?q=80&w=1000&auto=format&fit=crop",
    color: "#e67e22",
    es_vertical: false,
    tipo_contenido: "BANNER",
  },
  {
    id: 2,
    titulo: "Feria de Emprendimiento Estudiantil",
    contenido:
      "Ven a conocer los proyectos de tus compañeros en la plaza central. Habrá stands, comida y música en vivo.",
    imagen_url:
      "https://images.unsplash.com/photo-1588702545922-e1e550c60955?q=80&w=400&auto=format&fit=crop",
    color: "#007b33",
    es_vertical: true,
    tipo_contenido: "BANNER",
  },
  {
    id: 15,
    titulo: "Olimpiadas de Programación 2025",
    contenido:
      "Demuestra tus habilidades de código en la competencia más esperada del año.",
    imagen_url:
      "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?q=80&w=1000&auto=format&fit=crop",
    color: "#2196f3",
    es_vertical: false,
    tipo_contenido: "BANNER",
  },
  {
    id: 16,
    titulo: "Jornada de Salud Mental",
    contenido:
      "Participa en talleres y charlas sobre bienestar mental. Atención psicológica disponible.",
    imagen_url:
      "https://images.unsplash.com/photo-1576091160550-2173dba999ef?q=80&w=1000&auto=format&fit=crop",
    color: "#9c27b0",
    es_vertical: true,
    archivos: [
      {
        id: 103,
        nombre: "flyer_salud_mental.jpg",
        url: "https://images.unsplash.com/photo-1576091160550-2173dba999ef?q=80&w=500",
      },
    ],
    tipo_contenido: "BANNER",
  },
  {
    id: 17,
    titulo: "Campeonato de Fútbol Estudiantil",
    contenido:
      "Apoya a tu facultad en el torneo interescolástico. Stands y animación en el estadio.",
    imagen_url:
      "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?q=80&w=1000&auto=format&fit=crop",
    color: "#f44336",
    es_vertical: false,
    tipo_contenido: "BANNER",
  },
  // --- EVENTOS ---
  {
    id: 3,
    titulo: "Taller De Danza",
    contenido:
      "Inscríbete en el nuevo taller semestral de danza contemporánea.",
    imagen_url: "",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "EVENTO",
  },
  {
    id: 6,
    titulo: "Congreso de Investigación Estudiantil",
    contenido:
      "Presenta tus trabajos de investigación en el congreso institucional.",
    imagen_url:
      "https://images.unsplash.com/photo-1552664730-d307ca884978?q=80&w=500&auto=format&fit=crop",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "EVENTO",
  },
  {
    id: 10,
    titulo: "Semana de Bienvenida 2025",
    contenido:
      "Actividades de integración para estudiantes nuevos. Juegos, charlas y networking.",
    imagen_url:
      "https://images.unsplash.com/photo-1552664730-d307ca884978?q=80&w=500&auto=format&fit=crop",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "EVENTO",
  },
  {
    id: 13,
    titulo: "Festival Cultural Institucional",
    contenido:
      "Celebra la diversidad con música, danza y exposiciones de arte estudiantil.",
    imagen_url:
      "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?q=80&w=500&auto=format&fit=crop",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "EVENTO",
  },
  // --- INFORMACIÓN ---
  {
    id: 5,
    titulo: "Becas Académicas Disponibles",
    contenido:
      "Consulta los requisitos y fechas de inscripción para las becas del semestre.",
    imagen_url:
      "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?q=80&w=500&auto=format&fit=crop",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "INFORMACION",
  },
  {
    id: 7,
    titulo: "Certificación en Competencias Digitales",
    contenido:
      "Obtén tu certificado completando el programa de competencias digitales.",
    imagen_url:
      "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?q=80&w=500&auto=format&fit=crop",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "INFORMACION",
  },
  {
    id: 11,
    titulo: "Biblioteca Digital Renovada",
    contenido:
      "Accede a miles de recursos académicos en nuestra plataforma digital rediseñada.",
    imagen_url:
      "https://images.unsplash.com/photo-150784272343-583f20270319?q=80&w=500&auto=format&fit=crop",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "INFORMACION",
  },
  // --- NOTICIAS ---
  {
    id: 4,
    titulo: "Nuevo Convenio Prácticas Profesionales",
    contenido:
      "Se ha firmado un nuevo convenio con empresas de la región. Revisa el documento adjunto.",
    imagen_url:
      "https://images.unsplash.com/photo-1552664730-d307ca884978?q=80&w=500&auto=format&fit=crop",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "NOTICIA",
    archivos: [
      {
        id: 101,
        nombre: "documento_convenio.pdf",
        url: "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
      },
      {
        id: 102,
        nombre: "flyer_practicas.jpg",
        url: "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?q=80&w=500",
      },
    ],
  },
  {
    id: 14,
    titulo: "Admisiones Abiertas Especializaciones",
    contenido:
      "Abre la convocatoria para nuevos programas de especialización profesional.",
    imagen_url:
      "https://images.unsplash.com/photo-1552664730-d307ca884978?q=80&w=500&auto=format&fit=crop",
    color: "#eaf4e6",
    es_vertical: false,
    tipo_contenido: "NOTICIA",
  },
];
