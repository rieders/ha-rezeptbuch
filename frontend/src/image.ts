// Fotos vor dem Upload im Browser verkleinern (max. 2400 px, JPEG): spart mobile Daten
// und bleibt unter HAs Upload-Limit. createImageBitmap wendet die EXIF-Drehung an.
export const MAX_UPLOAD_DIMENSION = 2400;

export function targetSize(width: number, height: number, max = MAX_UPLOAD_DIMENSION): [number, number] {
  const longest = Math.max(width, height);
  if (longest <= max) return [width, height];
  const factor = max / longest;
  return [Math.round(width * factor), Math.round(height * factor)];
}

export async function downscale(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    const [w, h] = targetSize(bitmap.width, bitmap.height);
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(bitmap, 0, 0, w, h);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    return blob ?? file;
  } catch {
    return file; // z. B. HEIC ohne Browser-Unterstützung → Server prüft und meldet
  }
}
