/**
 * Sinh ma yeu cau 12 ky tu hex gui kem tieu de X-Ma-Yeu-Cau, cung dinh dang voi ma do
 * backend tu sinh, de noi chuoi truy vet tu giao dien toi nhat ky may chu.
 */
export function taoMaYeuCau(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '').slice(0, 12);
  }
  return Array.from({ length: 12 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
}
