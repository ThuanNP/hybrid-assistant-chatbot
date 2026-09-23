import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from './api.service';
import { KICH_THUOC_TRANG_HOI_THOAI, KhoHoiThoai } from './kho-hoi-thoai';
import { HoiThoai } from './mo-hinh';

function taoHoiThoai(id: number): HoiThoai {
  return { id, tieu_de: `Hội thoại ${id}`, tao_luc: '', cap_nhat_luc: '' };
}

describe('KhoHoiThoai (phân trang cuộn vô hạn)', () => {
  const tongSo = KICH_THUOC_TRANG_HOI_THOAI + 5;
  const tatCa = Array.from({ length: tongSo }, (_, i) => taoHoiThoai(i + 1));
  const layDanhSach = vi.fn((trang: number, kichThuoc: number) =>
    of({
      danh_sach: tatCa.slice((trang - 1) * kichThuoc, trang * kichThuoc),
      tong_so: tongSo,
      trang,
      kich_thuoc: kichThuoc,
    }),
  );

  beforeEach(() => {
    layDanhSach.mockClear();
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: ApiService, useValue: { layDanhSachHoiThoai: layDanhSach } },
      ],
    });
  });

  it('tải trang đầu, tải thêm trang kế tiếp rồi dừng khi đã đủ tổng số', () => {
    const kho = TestBed.inject(KhoHoiThoai);
    kho.taiLai();
    expect(kho.danhSach().length).toBe(KICH_THUOC_TRANG_HOI_THOAI);
    expect(kho.conThem()).toBe(true);

    kho.taiThem();
    expect(layDanhSach).toHaveBeenLastCalledWith(2, KICH_THUOC_TRANG_HOI_THOAI, {});
    expect(kho.danhSach().length).toBe(tongSo);
    expect(kho.conThem()).toBe(false);

    kho.taiThem();
    expect(layDanhSach).toHaveBeenCalledTimes(2);
  });

  it('bỏ mục trùng khi trang bị dịch do có hội thoại mới chen lên đầu', () => {
    const kho = TestBed.inject(KhoHoiThoai);
    kho.taiLai();
    layDanhSach.mockReturnValueOnce(
      of({ danh_sach: [taoHoiThoai(30), taoHoiThoai(31)], tong_so: tongSo, trang: 2, kich_thuoc: 30 }),
    );
    kho.taiThem();
    const cacId = kho.danhSach().map((ht) => ht.id);
    expect(new Set(cacId).size).toBe(cacId.length);
    expect(cacId.at(-1)).toBe(31);
  });

  it('danh sách lọc riêng giữ bộ lọc khi tải thêm và không đụng danh sách của kho', () => {
    const kho = TestBed.inject(KhoHoiThoai);
    kho.taiLai();
    const dsLoc = kho.taoDanhSachLoc();
    const boLoc = { tuKhoa: 'biểu giá', sapXep: 'cu_nhat' as const };

    dsLoc.taiLai(boLoc);
    dsLoc.taiThem();

    expect(layDanhSach).toHaveBeenLastCalledWith(2, KICH_THUOC_TRANG_HOI_THOAI, boLoc);
    dsLoc.boMuc(1);
    expect(dsLoc.danhSach().some((ht) => ht.id === 1)).toBe(false);
    expect(kho.danhSach().some((ht) => ht.id === 1)).toBe(true);
  });
});
