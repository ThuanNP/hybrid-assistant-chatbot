import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { BoCucTrang } from '../../core/bo-cuc-trang';
import { KhoHoiThoai } from '../../core/kho-hoi-thoai';
import { HuongDanComponent } from './huong-dan';
import { phanTichHuongDan, tachPhanChu } from './phan-tich-huong-dan';

const TAI_LIEU_MAU = [
  '# Hướng dẫn sử dụng',
  '',
  'Phần giới thiệu không hiển thị.',
  '',
  '## Trợ lý làm được gì',
  '',
  '### Làm được',
  '',
  '- Soạn thảo văn bản.',
  '- Tóm tắt nội dung.',
  '',
  '### Chưa làm được',
  '',
  '- Tra cứu tài liệu nội bộ.',
  '',
  '## Ba bước bắt đầu',
  '',
  '1. **Đăng nhập tài khoản**: Đăng nhập bằng email được cấp.',
  '2. **Tạo cuộc trò chuyện**: Bấm Cuộc trò chuyện mới.',
  '',
  '## Đặt câu hỏi rõ ràng',
  '',
  'Nêu rõ mục đích.',
  '',
  '> **Ví dụ:** Soạn giúp tôi thông báo,',
  '> giọng văn trang trọng.',
  '',
  '## Đọc kết quả trả lời',
  '',
  '- **Nội bộ**: xử lý trên máy chủ nội bộ',
  '- **Đám mây**: xử lý bởi dịch vụ đám mây',
  '- Mỗi câu trả lời có nhãn AI.',
  '',
  '## Dữ liệu không được nhập',
  '',
  '> Không nhập số điện thoại của khách hàng.',
  '',
  '## Khi gặp sự cố',
  '',
  'Sao chép mã yêu cầu.',
  '',
  '`ma_yeu_cau: 7f3a9c21b04e`',
].join('\n');

describe('phanTichHuongDan (nội dung Markdown -> khối có kiểu)', () => {
  const cacMuc = phanTichHuongDan(TAI_LIEU_MAU);

  it('mỗi tiêu đề ## là một mục có id neo không dấu; phần trước ## đầu tiên bị bỏ qua', () => {
    expect(cacMuc.map((m) => m.id)).toEqual([
      'tro-ly-lam-duoc-gi',
      'ba-buoc-bat-dau',
      'dat-cau-hoi-ro-rang',
      'doc-ket-qua-tra-loi',
      'du-lieu-khong-duoc-nhap',
      'khi-gap-su-co',
    ]);
  });

  it('hai tiêu đề ### liên tiếp thành một nhóm thẻ Làm được / Chưa làm được', () => {
    expect(cacMuc[0].cacKhoi).toEqual([
      {
        loai: 'nhom-the',
        cacThe: [
          { tieuDe: 'Làm được', kieu: 'dat', cacMuc: [tachPhanChu('Soạn thảo văn bản.'), tachPhanChu('Tóm tắt nội dung.')] },
          { tieuDe: 'Chưa làm được', kieu: 'chua-dat', cacMuc: [tachPhanChu('Tra cứu tài liệu nội bộ.')] },
        ],
      },
    ]);
  });

  it('danh sách đánh số có tiêu đề đậm thành các thẻ bước', () => {
    expect(cacMuc[1].cacKhoi).toEqual([
      {
        loai: 'cac-buoc',
        cacBuoc: [
          { tieuDe: 'Đăng nhập tài khoản', moTa: 'Đăng nhập bằng email được cấp.' },
          { tieuDe: 'Tạo cuộc trò chuyện', moTa: 'Bấm Cuộc trò chuyện mới.' },
        ],
      },
    ]);
  });

  it('trích dẫn bắt đầu bằng Ví dụ thành khung ví dụ, gộp nhiều dòng', () => {
    const [doan, viDu] = cacMuc[2].cacKhoi;
    expect(doan.loai).toBe('doan');
    expect(viDu).toEqual({
      loai: 'vi-du',
      noiDung: tachPhanChu('Soạn giúp tôi thông báo, giọng văn trang trọng.'),
    });
  });

  it('mục Nội bộ / Đám mây thành huy hiệu đứng trước danh sách thường', () => {
    const [huyHieu, danhSach] = cacMuc[3].cacKhoi;
    expect(huyHieu).toEqual({
      loai: 'huy-hieu',
      cacHuyHieu: [
        { nhan: 'Nội bộ', moTa: 'xử lý trên máy chủ nội bộ', kieu: 'noi-bo' },
        { nhan: 'Đám mây', moTa: 'xử lý bởi dịch vụ đám mây', kieu: 'dam-may' },
      ],
    });
    expect(danhSach.loai).toBe('danh-sach');
  });

  it('trích dẫn thường thành khung cảnh báo; đoạn chỉ gồm mã thành chip mã', () => {
    expect(cacMuc[4].cacKhoi[0].loai).toBe('canh-bao');
    expect(cacMuc[5].cacKhoi[1]).toEqual({ loai: 'ma', ma: 'ma_yeu_cau: 7f3a9c21b04e' });
  });

  it('tách chữ đậm và mã nội dòng', () => {
    expect(tachPhanChu('Nhãn **AI** và `ma`')).toEqual([
      { chu: 'Nhãn ', dam: false, ma: false },
      { chu: 'AI', dam: true, ma: false },
      { chu: ' và ', dam: false, ma: false },
      { chu: 'ma', dam: false, ma: true },
    ]);
  });
});

describe('HuongDanComponent (màn Hướng dẫn sử dụng theo bản Stitch)', () => {
  let component: HuongDanComponent;
  let fixture: ComponentFixture<HuongDanComponent>;
  let mockKho: { moHoiThoaiMoi: ReturnType<typeof vi.fn> };

  const mockFaqData = {
    phien_ban: '2026-09-24.2',
    muc: [
      { ma: 'TG-01', nhom: 'bat_dau', cau_hoi: 'Tôi đăng nhập bằng tài khoản nào?', tra_loi: 'Dùng email nội bộ.' },
      { ma: 'TG-02', nhom: 'bat_dau', cau_hoi: 'Quên mật khẩu thì liên hệ ai?', tra_loi: 'Liên hệ CNTT.' },
      { ma: 'TG-05', nhom: 'dat_cau_hoi', cau_hoi: 'Đặt câu hỏi thế nào?', tra_loi: 'Nêu rõ bối cảnh.' },
    ],
  };

  beforeEach(async () => {
    mockKho = { moHoiThoaiMoi: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [HuongDanComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        {
          provide: ApiService,
          useValue: {
            layCauHoiThuongGap: () => of(mockFaqData),
            layHuongDanSuDung: () => of({ phien_ban: '1', noi_dung: TAI_LIEU_MAU }),
          },
        },
        { provide: KhoHoiThoai, useValue: mockKho },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HuongDanComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('tiêu đề và mô tả trang theo bản Stitch', () => {
    const boCuc = TestBed.inject(BoCucTrang);
    expect(boCuc.tieuDe()).toBe('Hướng dẫn sử dụng');
    expect(boCuc.moTa()).toContain('câu hỏi thường gặp');
  });

  it('mục lục bắt đầu bằng Câu hỏi thường gặp, tiếp theo là các mục của tài liệu', () => {
    const el = fixture.nativeElement as HTMLElement;
    const cacNut = [...el.querySelectorAll('.nut-muc-luc')].map((n) => n.textContent?.trim());
    expect(cacNut[0]).toBe('Câu hỏi thường gặp');
    expect(cacNut.slice(1)).toEqual([
      'Trợ lý làm được gì',
      'Ba bước bắt đầu',
      'Đặt câu hỏi rõ ràng',
      'Đọc kết quả trả lời',
      'Dữ liệu không được nhập',
      'Khi gặp sự cố',
    ]);
  });

  it('năm thẻ nhóm, mặc định Bắt đầu, câu đầu của nhóm mở sẵn; không có ô tìm hay mã TG', () => {
    const el = fixture.nativeElement as HTMLElement;
    const cacChip = [...el.querySelectorAll('.chip-nhom')].map((c) => c.textContent?.trim());
    expect(cacChip).toEqual(['Bắt đầu', 'Đặt câu hỏi', 'Đọc kết quả', 'Lịch sử', 'Sự cố và dữ liệu']);
    expect(el.querySelector('.chip-nhom.dang-chon')?.textContent?.trim()).toBe('Bắt đầu');
    expect(el.querySelectorAll('.the-faq').length).toBe(2);
    expect(component.cauHoiDangMo()).toBe('TG-01');
    expect(el.querySelector('input')).toBeNull();
    expect(el.textContent).not.toContain('TG-01');
  });

  it('đổi nhóm thì mở câu đầu của nhóm mới; bấm lại câu đang mở thì đóng', async () => {
    component.chuyenNhom('dat_cau_hoi');
    await fixture.whenStable();
    expect(component.faqHienThi().map((m) => m.ma)).toEqual(['TG-05']);
    expect(component.cauHoiDangMo()).toBe('TG-05');

    component.chuyenDoiAccordion('TG-05');
    expect(component.cauHoiDangMo()).toBeNull();
  });

  it('nút Hỏi trợ lý mở cuộc trò chuyện mới với đúng câu hỏi của mục', async () => {
    const el = fixture.nativeElement as HTMLElement;
    el.querySelector<HTMLButtonElement>('.nut-hoi-tro-ly')?.click();
    expect(mockKho.moHoiThoaiMoi).toHaveBeenCalledWith('Tôi đăng nhập bằng tài khoản nào?');
  });

  it('dựng đủ các khối của tài liệu: thẻ khả năng, bước, ví dụ, huy hiệu, cảnh báo, chip mã', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelectorAll('.the-kha-nang').length).toBe(2);
    expect(el.querySelector('.the-kha-nang.chua-dat')).not.toBeNull();
    expect(el.querySelectorAll('.the-buoc').length).toBe(2);
    expect(el.querySelector('.khung-vi-du')?.textContent).toContain('Ví dụ:');
    expect(el.querySelectorAll('.huy-hieu-tang').length).toBe(2);
    expect(el.querySelector('.khung-canh-bao')).not.toBeNull();
    expect(el.querySelector('.chip-ma code')?.textContent).toBe('ma_yeu_cau: 7f3a9c21b04e');
  });
});
