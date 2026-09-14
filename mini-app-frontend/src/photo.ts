/** Decode and re-encode locally: limit upload size and remove image metadata. */
export async function preparePhoto(file: File): Promise<string> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 12 * 1024 * 1024) {
    throw new Error('Выберите JPEG, PNG или WebP до 12 МБ. Для HEIC сохраните фото как JPEG.');
  }
  const url = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = url;
    await image.decode();
    if (!image.naturalWidth || image.naturalWidth * image.naturalHeight > 40_000_000) {
      throw new Error('Фото слишком большое. Выберите снимок до 40 мегапикселей.');
    }
    const scale = Math.min(1, 1600 / Math.max(image.naturalWidth, image.naturalHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(image.naturalWidth * scale);
    canvas.height = Math.round(image.naturalHeight * scale);
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Не удалось обработать фото на этом устройстве.');
    context.fillStyle = '#fff';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    let encoded = canvas.toDataURL('image/jpeg', 0.85).split(',')[1];
    if (encoded.length > 1_800_000) encoded = canvas.toDataURL('image/jpeg', 0.65).split(',')[1];
    if (!encoded || encoded.length > 1_800_000) throw new Error('Фото слишком большое. Снимите меньше пачек за один раз.');
    canvas.width = canvas.height = 1;
    return encoded;
  } finally {
    URL.revokeObjectURL(url);
  }
}
