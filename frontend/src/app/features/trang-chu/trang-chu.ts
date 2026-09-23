import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { BoCucTrang } from '../../core/bo-cuc-trang';
import { dinhDangNgayDai, dinhDangNgayGio } from '../../core/dinh-dang';
import { KhoHoiThoai } from '../../core/kho-hoi-thoai';
import { BaoCaoChiPhi, TrangThaiHangDoi } from '../../core/mo-hinh';
import { DANH_SACH_TAC_VU_NHANH, TacVuNhanh } from '../../core/tac-vu-nhanh';
import { BieuTuongComponent } from '../../shared/bieu-tuong/bieu-tuong';
import { OSoanCauHoiComponent } from '../../shared/o-soan-cau-hoi/o-soan-cau-hoi';

const SO_HOI_THOAI_TREN_TRANG_CHU = 7;
/** Thanh lap day hang doi chuyen mau canh bao tu 80% suc chua (chi la hien thi). */
const NGUONG_LAP_DAY_HANG_DOI = 80;
const CHU_VI_VONG_TIEN_DO = 2 * Math.PI * 30;

const DINH_DANG_SO = new Intl.NumberFormat('vi-VN');
const DINH_DANG_THAP_PHAN = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 });
const DINH_DANG_USD = new Intl.NumberFormat('vi-VN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

/**
 * Trang chu (DESIGN.md muc 6.4, 6.5, 8.5): chi hien thi so lieu va loi tat.
 * Moi cau hoi bat dau tu day deu chuyen sang man Tro chuyen, khong tro chuyen tai cho.
 */
@Component({
  selector: 'app-trang-chu',
  imports: [RouterLink, BieuTuongComponent, OSoanCauHoiComponent],
  templateUrl: './trang-chu.html',
  styleUrl: './trang-chu.scss',
})
export class TrangChuComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly boCuc = inject(BoCucTrang);
  protected readonly kho = inject(KhoHoiThoai);

  public readonly ngayHomNay = dinhDangNgayDai(new Date());
  public readonly cacTacVu = DANH_SACH_TAC_VU_NHANH;
  public readonly chuViVong = CHU_VI_VONG_TIEN_DO;

  public readonly chiPhi = signal<BaoCaoChiPhi | null>(null);
  public readonly hangDoi = signal<TrangThaiHangDoi | null>(null);
  public readonly cauHoiNhap = signal('');

  public readonly hoiThoaiGanDay = computed(() =>
    this.kho.danhSach().slice(0, SO_HOI_THOAI_TREN_TRANG_CHU),
  );

  /** So cau hoi trong ngay do may chu dem tren bang luot (gio Viet Nam). */
  public readonly tongLuotHomNay = computed(() => this.chiPhi()?.so_cau_hoi_hom_nay ?? null);
  public readonly luotDamMay = computed(() => this.chiPhi()?.so_cau_hoi_dam_may ?? 0);
  public readonly luotNoiBo = computed(() => this.chiPhi()?.so_cau_hoi_noi_bo ?? 0);
  /** Ty le cau tra loi noi bo tren tong cau tra loi, de ve vong tron. */
  public readonly phanTramLuotNoiBo = computed(() => {
    const tong = this.luotNoiBo() + this.luotDamMay();
    return tong > 0 ? (this.luotNoiBo() / tong) * 100 : 0;
  });

  public readonly nguongLapDayHangDoi = NGUONG_LAP_DAY_HANG_DOI;
  /** Muc lap day hang doi theo suc chua toi da do may chu cau hinh. */
  public readonly phanTramHangDoi = computed(() => {
    const hd = this.hangDoi();
    const toiDa = hd?.do_dai_toi_da ?? 0;
    if (!hd || toiDa <= 0) return 0;
    return Math.min(100, (hd.dang_cho / toiDa) * 100);
  });

  /** `ty_le_local` la phan so 0-1; doi ra phan tram de hien thi. */
  public readonly tyLeLocal = computed(() => {
    const tyLe = this.chiPhi()?.ty_le_local;
    return tyLe === undefined ? null : tyLe * 100;
  });
  public readonly phanTramNganSach = computed(() =>
    Math.min(100, this.chiPhi()?.phan_tram_da_dung ?? 0),
  );
  /** Nguong canh bao ngan sach doc tu cau hinh may chu. */
  public readonly vuotNguongNganSach = computed(() => {
    const chiPhi = this.chiPhi();
    return chiPhi !== null && chiPhi.phan_tram_da_dung >= chiPhi.nguong_canh_bao_ngan_sach * 100;
  });

  public ngOnInit(): void {
    this.boCuc.datTieuDe('Trang chủ', [], null, `Xin chào Anh/Chị · ${this.ngayHomNay}`);
    this.kho.taiLai();
    this.api.layChiPhi().subscribe({ next: (kq) => this.chiPhi.set(kq), error: () => {} });
    this.api.layTrangThaiHangDoi().subscribe({ next: (kq) => this.hangDoi.set(kq), error: () => {} });
  }

  public batDauHoi(cauHoi: string): void {
    this.kho.moHoiThoaiMoi(cauHoi);
  }

  public chonTacVu(tacVu: TacVuNhanh): void {
    this.kho.moHoiThoaiMoi(tacVu.cauHoi);
  }

  public doLechVong(phanTram: number): number {
    return this.chuViVong * (1 - Math.min(100, Math.max(0, phanTram)) / 100);
  }

  public dinhDangSo(so: number): string {
    return DINH_DANG_SO.format(so);
  }

  public dinhDangPhanTram(phanTram: number): string {
    return `${this.dinhDangSoThapPhan(phanTram)}%`;
  }

  /** So thap phan mot chu so theo kieu Viet Nam (dau phay thap phan). */
  public dinhDangSoThapPhan(so: number): string {
    return DINH_DANG_THAP_PHAN.format(so);
  }

  public dinhDangUsd(so: number): string {
    return `${DINH_DANG_USD.format(so)} USD`;
  }

  public dinhDangThoiGian(chuoiIso: string): string {
    return dinhDangNgayGio(chuoiIso);
  }
}
