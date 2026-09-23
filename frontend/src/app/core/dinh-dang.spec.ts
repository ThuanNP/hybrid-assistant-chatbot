import { dinhDangMocGon, xepNhomThoiGian } from './dinh-dang';

describe('dinh-dang (nhóm thời gian và mốc gọn của màn Lịch sử)', () => {
  const bayGio = new Date(2026, 8, 23, 17, 0);

  it('chỉ có ba nhóm: Hôm nay, Hôm qua, Cũ hơn (không còn nhóm 7 ngày qua)', () => {
    expect(xepNhomThoiGian(new Date(2026, 8, 23, 8, 0).toISOString(), bayGio)).toBe('Hôm nay');
    expect(xepNhomThoiGian(new Date(2026, 8, 22, 23, 59).toISOString(), bayGio)).toBe('Hôm qua');
    expect(xepNhomThoiGian(new Date(2026, 8, 21, 12, 0).toISOString(), bayGio)).toBe('Cũ hơn');
    expect(xepNhomThoiGian(new Date(2026, 5, 1).toISOString(), bayGio)).toBe('Cũ hơn');
    expect(xepNhomThoiGian('khong-phai-ngay', bayGio)).toBe('Cũ hơn');
  });

  it('mốc gọn: hôm nay, hôm qua ghi giờ; cùng năm ghi dd/mm; khác năm ghi dd/mm/yyyy', () => {
    expect(dinhDangMocGon(new Date(2026, 8, 23, 14, 30).toISOString(), bayGio)).toBe('14:30');
    expect(dinhDangMocGon(new Date(2026, 8, 22, 9, 5).toISOString(), bayGio)).toBe('09:05');
    expect(dinhDangMocGon(new Date(2026, 8, 2, 10, 0).toISOString(), bayGio)).toBe('02/09');
    expect(dinhDangMocGon(new Date(2025, 11, 31, 10, 0).toISOString(), bayGio)).toBe('31/12/2025');
  });
});
