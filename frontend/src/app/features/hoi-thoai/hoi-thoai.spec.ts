import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { BoCucTrang } from '../../core/bo-cuc-trang';
import { KhoHoiThoai } from '../../core/kho-hoi-thoai';
import {
  BoLocHoiThoai,
  DanhSachHoiThoai,
  HoiThoai,
  PhanHoiXoaHoiThoai,
} from '../../core/mo-hinh';
import { HoiThoaiComponent } from './hoi-thoai';

describe('HoiThoaiComponent (màn Lịch sử hội thoại)', () => {
  let component: HoiThoaiComponent;
  let fixture: ComponentFixture<HoiThoaiComponent>;

  const bayGio = new Date().toISOString();
  const tatCa: HoiThoai[] = [
    { id: 1, tieu_de: 'Tra cứu quy định cấp điện', tao_luc: bayGio, cap_nhat_luc: bayGio },
    {
      id: 2,
      tieu_de: 'Biểu giá bán lẻ điện',
      tao_luc: '2020-01-01T08:00:00Z',
      cap_nhat_luc: '2020-01-01T08:00:00Z',
    },
  ];

  /** Gia lap may chu: loc tu khoa, khoang ngay va sap xep, `tong_so` dem theo bo loc. */
  function mayChuGia(boLoc: BoLocHoiThoai): DanhSachHoiThoai {
    const tuKhoa = (boLoc.tuKhoa ?? '').toLocaleLowerCase('vi');
    const ngay = (ht: HoiThoai): string => ht.cap_nhat_luc.slice(0, 10);
    let ds = tatCa.filter(
      (ht) =>
        ht.tieu_de.toLocaleLowerCase('vi').includes(tuKhoa) &&
        (!boLoc.tuNgay || ngay(ht) >= boLoc.tuNgay) &&
        (!boLoc.denNgay || ngay(ht) <= boLoc.denNgay),
    );
    if (boLoc.sapXep === 'cu_nhat') ds = [...ds].reverse();
    if (boLoc.sapXep === 'ten_tang') ds = [...ds].sort((a, b) => a.tieu_de.localeCompare(b.tieu_de, 'vi'));
    if (boLoc.sapXep === 'ten_giam') ds = [...ds].sort((a, b) => b.tieu_de.localeCompare(a.tieu_de, 'vi'));
    return { danh_sach: ds, tong_so: ds.length, trang: 1, kich_thuoc: 30 };
  }

  const mockPhanHoiXoa: PhanHoiXoaHoiThoai = {
    thanh_cong: true,
    thong_diep: 'Đã xoá cuộc hội thoại.',
  };

  const layDanhSach = vi.fn((_trang: number, _kichThuoc: number, boLoc: BoLocHoiThoai = {}) =>
    of(mayChuGia(boLoc)),
  );

  const mockApiService = {
    layDanhSachHoiThoai: layDanhSach,
    xoaHoiThoai: (_id: number) => of(mockPhanHoiXoa),
  };

  function boLocGanNhat(): BoLocHoiThoai {
    return layDanhSach.mock.lastCall?.[2] ?? {};
  }

  beforeEach(async () => {
    layDanhSach.mockClear();
    await TestBed.configureTestingModule({
      imports: [HoiThoaiComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([{ path: 'tro-chuyen/:id', children: [] }]),
        { provide: ApiService, useValue: mockApiService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HoiThoaiComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('tải danh sách và xếp vào nhóm thời gian', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Tra cứu quy định cấp điện');
    expect(el.textContent).toContain('Biểu giá bán lẻ điện');
    expect(component.cacNhom().map((n) => n.ten)).toEqual(['Hôm nay', 'Cũ hơn']);
  });

  it('mặc định Từ ngày, Đến ngày là null: không gửi bộ lọc ngày, hiển thị toàn bộ lịch sử', async () => {
    expect(component.tuNgay()).toBeNull();
    expect(component.denNgay()).toBeNull();
    expect(component.coLocNangCao()).toBe(false);
    expect(boLocGanNhat().tuNgay).toBeNull();

    // Xoa trang o ngay sau khi da chon thi tro ve null, khong loc
    component.tuNgay.set('2026-09-01');
    const o = document.createElement('input');
    o.value = '';
    component.chonNgay(component.tuNgay, { target: o } as unknown as Event);
    await fixture.whenStable();
    expect(component.tuNgay()).toBeNull();
    expect(boLocGanNhat().tuNgay).toBeNull();
  });

  it('mỗi ô ngày có nút xoá riêng, chỉ hiện khi ô có giá trị, bấm thì ô về null', async () => {
    const el = fixture.nativeElement as HTMLElement;
    component.hienNangCao.set(true);
    await fixture.whenStable();
    expect(el.querySelectorAll('.nut-xoa-ngay').length).toBe(0);

    component.tuNgay.set('2026-09-01');
    component.denNgay.set('2026-09-23');
    await fixture.whenStable();
    el.querySelector<HTMLButtonElement>('button[aria-label="Xoá ngày bắt đầu"]')?.click();
    await fixture.whenStable();
    expect(component.tuNgay()).toBeNull();
    expect(component.denNgay()).toBe('2026-09-23');

    el.querySelector<HTMLButtonElement>('button[aria-label="Xoá ngày kết thúc"]')?.click();
    await fixture.whenStable();
    expect(component.denNgay()).toBeNull();
    expect(el.querySelectorAll('.nut-xoa-ngay').length).toBe(0);
  });

  it('dòng phụ của mục ghi số lượt và thời điểm cập nhật', () => {
    const moTa = component.moTaMuc({ ...tatCa[1], so_luot: 8 });
    expect(moTa).toBe('8 lượt · cập nhật 01/01/2020');
  });

  it('mỗi mục là liên kết mở màn Trò chuyện của hội thoại đó', () => {
    const el = fixture.nativeElement as HTMLElement;
    const lienKet = el.querySelector<HTMLAnchorElement>('.lien-ket-muc');
    expect(lienKet?.getAttribute('href')).toBe('/tro-chuyen/1');
  });

  it('tìm kiếm nâng cao ẩn mặc định, mở bằng nút biểu tượng trong ô tìm có tooltip', async () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.nang-cao')).toBeNull();

    const nut = el.querySelector<HTMLButtonElement>('.o-tim-kiem button[aria-label="Tìm kiếm nâng cao"]');
    expect(nut?.getAttribute('data-goi-y')).toBe('Tìm kiếm nâng cao');
    nut?.click();
    await fixture.whenStable();
    expect(el.querySelector('.nang-cao')).not.toBeNull();
    expect(nut?.getAttribute('aria-expanded')).toBe('true');

    nut?.click();
    await fixture.whenStable();
    component.tuNgay.set('2026-09-01');
    await fixture.whenStable();
    expect(el.querySelector('.cham-dang-loc')).not.toBeNull();
  });

  it('sắp xếp gửi lên máy chủ; theo tên thì một danh sách phẳng, cũ nhất đảo thứ tự nhóm', async () => {
    component.sapXep.set('ten_tang');
    await fixture.whenStable();
    expect(boLocGanNhat().sapXep).toBe('ten_tang');
    expect(component.cacNhom().map((n) => n.ten)).toEqual(['Theo tên A → Z']);
    expect(component.cacNhom()[0].cacMuc.map((ht) => ht.id)).toEqual([2, 1]);

    component.sapXep.set('ten_giam');
    await fixture.whenStable();
    expect(component.cacNhom()[0].cacMuc.map((ht) => ht.id)).toEqual([1, 2]);

    component.sapXep.set('cu_nhat');
    await fixture.whenStable();
    expect(component.cacNhom().map((n) => n.ten)).toEqual(['Cũ hơn', 'Hôm nay']);
  });

  it('lọc theo khoảng ngày ở máy chủ; không có kết quả thì hiện minh hoạ và nút Xoá lọc', async () => {
    component.tuNgay.set('2020-01-01');
    component.denNgay.set('2020-01-02');
    await fixture.whenStable();
    expect(boLocGanNhat()).toMatchObject({ tuNgay: '2020-01-01', denNgay: '2020-01-02' });
    expect(component['ds'].danhSach().map((ht) => ht.id)).toEqual([2]);

    component.tuNgay.set('2019-01-01');
    component.denNgay.set('2019-01-31');
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.minh-hoa-trong')).not.toBeNull();
    expect(el.querySelector('.tieu-de-trong')?.textContent).toContain('Không tìm thấy');

    component.xoaBoLoc();
    await fixture.whenStable();
    expect(component['ds'].danhSach().length).toBe(2);
    expect(el.querySelector('.minh-hoa-trong')).toBeNull();
  });

  it('Enter gửi từ khoá lên máy chủ ngay, không chờ hết thời gian gõ', async () => {
    component.tuKhoa.set('BIỂU GIÁ');
    component.timLai();
    await fixture.whenStable();
    expect(boLocGanNhat().tuKhoa).toBe('BIỂU GIÁ');
    expect(component['ds'].danhSach().map((ht) => ht.id)).toEqual([2]);
  });

  it('dòng mô tả không ghi tổng số; khi đang lọc ghi số kết quả do máy chủ đếm', async () => {
    const boCuc = TestBed.inject(BoCucTrang);
    expect(boCuc.tieuDe()).toBe('Lịch sử hội thoại');
    expect(boCuc.duongDan()).toEqual([{ nhan: 'Lịch sử hội thoại', lienKet: null }]);
    expect(boCuc.moTa()).toBe('Tìm và mở lại các cuộc trò chuyện trước đây');

    component.tuKhoa.set('biểu giá');
    component.timLai();
    await fixture.whenStable();
    expect(boCuc.moTa()).toBe('Tìm thấy 1 cuộc trò chuyện');
  });

  it('cuối danh sách ghi "Đã hiển thị toàn bộ", không ghi phân số', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.moc-tai-them')?.textContent?.trim()).toBe('Đã hiển thị toàn bộ');
  });

  it('mở hộp thoại xác nhận xoá của ứng dụng và đóng khi Huỷ (không dùng window.confirm)', async () => {
    component.moXacNhanXoa(tatCa[0], new MouseEvent('click'));
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    const hopThoai = el.querySelector('.hop-thoai-the');
    expect(hopThoai?.textContent).toContain('Xác nhận xoá hội thoại');

    component.dongXacNhanXoa();
    expect(component.hoiThoaiDangXoa()).toBeNull();
  });

  it('xác nhận xoá bỏ hội thoại khỏi danh sách đang hiện và khỏi kho dùng chung', async () => {
    const kho = TestBed.inject(KhoHoiThoai);
    kho.taiLai();
    component.moXacNhanXoa(tatCa[0], new MouseEvent('click'));
    component.thucHienXoa();
    await fixture.whenStable();

    expect(component['ds'].danhSach().find((ht) => ht.id === 1)).toBeUndefined();
    expect(kho.danhSach().find((ht) => ht.id === 1)).toBeUndefined();
    expect(kho.tongSo()).toBe(1);
    expect(component.hoiThoaiDangXoa()).toBeNull();
  });
});
