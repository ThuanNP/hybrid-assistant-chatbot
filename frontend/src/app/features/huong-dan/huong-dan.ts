import { NgTemplateOutlet } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ApiService } from '../../core/api.service';
import { BoCucTrang } from '../../core/bo-cuc-trang';
import { KhoHoiThoai } from '../../core/kho-hoi-thoai';
import { MucCauHoiThuongGap } from '../../core/mo-hinh';
import { BieuTuongComponent } from '../../shared/bieu-tuong/bieu-tuong';
import { MucHuongDan, phanTichHuongDan } from './phan-tich-huong-dan';

export interface MucLuc {
  readonly id: string;
  readonly tieuDe: string;
}

export interface ChipNhom {
  readonly ma: string;
  readonly nhan: string;
}

/** Nam nhom cau hoi thuong gap theo thu tu ban Stitch; nhom dau duoc chon mac dinh. */
const CAC_CHIP_NHOM: readonly ChipNhom[] = [
  { ma: 'bat_dau', nhan: 'Bắt đầu' },
  { ma: 'dat_cau_hoi', nhan: 'Đặt câu hỏi' },
  { ma: 'doc_ket_qua', nhan: 'Đọc kết quả' },
  { ma: 'lich_su', nhan: 'Lịch sử' },
  { ma: 'su_co_va_du_lieu', nhan: 'Sự cố và dữ liệu' },
];

const ID_CAU_HOI_THUONG_GAP = 'cau-hoi-thuong-gap';
/** Khoang lech (px) tu mep tren vung cuon de coi mot muc la dang doc. */
const LECH_THEO_DOI_MUC = 48;

/**
 * Man Huong dan su dung (ban Stitch "Huong dan su dung · Tro ly noi bo"): muc luc co dinh ben
 * trai, the noi dung ben phai la vung cuon duy nhat; cau hoi thuong gap dung dau, sau do cac muc
 * cua config/huong_dan_su_dung.md. Giao dien va loi nhac dung chung hai nguon noi dung nay.
 */
@Component({
  selector: 'app-huong-dan',
  imports: [BieuTuongComponent, NgTemplateOutlet],
  templateUrl: './huong-dan.html',
  styleUrl: './huong-dan.scss',
})
export class HuongDanComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly boCuc = inject(BoCucTrang);
  private readonly kho = inject(KhoHoiThoai);

  public readonly chipsNhom = CAC_CHIP_NHOM;
  public readonly idCauHoiThuongGap = ID_CAU_HOI_THUONG_GAP;
  public readonly nhomDangChon = signal<string>(CAC_CHIP_NHOM[0].ma);
  public readonly cauHoiDangMo = signal<string | null>(null);

  public readonly danhSachFaq = signal<MucCauHoiThuongGap[]>([]);
  public readonly cacMucHuongDan = signal<MucHuongDan[]>([]);
  public readonly mucLucActive = signal<string>(ID_CAU_HOI_THUONG_GAP);
  public readonly maDaSaoChep = signal<string | null>(null);

  public readonly dangTai = signal<boolean>(true);
  public readonly loi = signal<string | null>(null);

  public readonly danhSachMucLuc = computed<MucLuc[]>(() => [
    { id: ID_CAU_HOI_THUONG_GAP, tieuDe: 'Câu hỏi thường gặp' },
    ...this.cacMucHuongDan().map((m) => ({ id: m.id, tieuDe: m.tieuDe })),
  ]);

  public readonly faqHienThi = computed(() =>
    this.danhSachFaq().filter((m) => m.nhom === this.nhomDangChon()),
  );

  public ngOnInit(): void {
    this.boCuc.datTieuDe(
      'Hướng dẫn sử dụng',
      [{ nhan: 'Hướng dẫn sử dụng', lienKet: null }],
      null,
      'Hướng dẫn ngắn và câu hỏi thường gặp giúp Anh/Chị bắt đầu dùng Trợ lý nội bộ.',
    );
    this.napDuLieu();
  }

  public napDuLieu(): void {
    this.dangTai.set(true);
    this.loi.set(null);

    this.api.layCauHoiThuongGap().subscribe({
      next: (res) => {
        this.danhSachFaq.set(res.muc ?? []);
        this.moMucDauCuaNhom();
      },
      error: () => this.loi.set('Không thể nạp danh mục câu hỏi thường gặp. Vui lòng thử lại sau.'),
    });

    this.api.layHuongDanSuDung().subscribe({
      next: (res) => {
        this.cacMucHuongDan.set(phanTichHuongDan(res.noi_dung ?? ''));
        this.dangTai.set(false);
      },
      error: () => {
        this.loi.set('Không thể nạp tài liệu hướng dẫn. Vui lòng thử lại sau.');
        this.dangTai.set(false);
      },
    });
  }

  public chuyenNhom(maNhom: string): void {
    this.nhomDangChon.set(maNhom);
    this.moMucDauCuaNhom();
  }

  /** Moi luc chi mo mot cau tra loi; bam lai muc dang mo thi dong. */
  public chuyenDoiAccordion(ma: string): void {
    this.cauHoiDangMo.set(this.cauHoiDangMo() === ma ? null : ma);
  }

  public laDangMo(ma: string): boolean {
    return this.cauHoiDangMo() === ma;
  }

  public hoiTroLy(cauHoi: string, suKien: Event): void {
    suKien.stopPropagation();
    this.kho.moHoiThoaiMoi(cauHoi);
  }

  public cuonToiMuc(id: string): void {
    this.mucLucActive.set(id);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /** Danh dau muc dang doc trong muc luc theo vi tri cuon cua the noi dung. */
  public theoDoiCuon(suKien: Event): void {
    const vung = suKien.target as HTMLElement;
    const cacMuc = this.danhSachMucLuc();
    // Cuon het cuoi: cac muc ngan cuoi trang khong bao gio cham moc tren, chon muc cuoi
    if (vung.scrollTop + vung.clientHeight >= vung.scrollHeight - 2) {
      this.mucLucActive.set(cacMuc.at(-1)?.id ?? ID_CAU_HOI_THUONG_GAP);
      return;
    }
    const mocTren = vung.getBoundingClientRect().top + LECH_THEO_DOI_MUC;
    let dangDoc = ID_CAU_HOI_THUONG_GAP;
    for (const muc of cacMuc) {
      const phanTu = document.getElementById(muc.id);
      if (phanTu && phanTu.getBoundingClientRect().top <= mocTren) dangDoc = muc.id;
    }
    this.mucLucActive.set(dangDoc);
  }

  public saoChepMa(ma: string): void {
    void navigator.clipboard?.writeText(ma).then(() => {
      this.maDaSaoChep.set(ma);
      setTimeout(() => this.maDaSaoChep.set(null), 2000);
    });
  }

  private moMucDauCuaNhom(): void {
    this.cauHoiDangMo.set(this.faqHienThi()[0]?.ma ?? null);
  }
}
