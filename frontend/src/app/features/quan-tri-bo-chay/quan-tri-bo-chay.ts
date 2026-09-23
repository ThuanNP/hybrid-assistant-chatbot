import { Component, DestroyRef, OnInit, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth/auth.service';
import { BoCucTrang } from '../../core/bo-cuc-trang';
import { TrangThaiBoChay } from '../../core/mo-hinh';
import { BieuTuongComponent } from '../../shared/bieu-tuong/bieu-tuong';

const DINH_DANG_GB = new Intl.NumberFormat('vi-VN', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 2,
});
const DINH_DANG_GIO = new Intl.DateTimeFormat('vi-VN', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

/** Chu ky tu lam moi (giay); 0 la tat. Chi doc /api/ps, /api/show nen chi phi rat nho. */
export const CAC_CHU_KY_TU_LAM_MOI: readonly { giay: number; nhan: string }[] = [
  { giay: 0, nhan: 'Tắt' },
  { giay: 15, nhan: '15 giây' },
  { giay: 30, nhan: '30 giây' },
  { giay: 60, nhan: '60 giây' },
];
/** Tuy chon hien thi rieng cua trinh duyet nay, khong phai cau hinh may chu. */
const KHOA_LUU_CHU_KY = 'tro-ly.bo-chay.tu-lam-moi-giay';

function docChuKyDaLuu(): number {
  try {
    const giay = Number(localStorage.getItem(KHOA_LUU_CHU_KY));
    return CAC_CHU_KY_TU_LAM_MOI.some((c) => c.giay === giay) ? giay : 0;
  } catch {
    return 0;
  }
}

/**
 * Trang quan tri tam thoi kiem tra tinh trang bo chay local (/quan-tri/bo-chay).
 * Danh rieng cho nguoi dung co vai tro quan_tri. Tu lam moi chi phuc vu theo doi truc tiep;
 * canh bao dinh ky da do tac vu nen cua may chu dam nhan (moi 60 giay).
 */
@Component({
  selector: 'app-quan-tri-bo-chay',
  imports: [RouterLink, BieuTuongComponent],
  templateUrl: './quan-tri-bo-chay.html',
  styleUrl: './quan-tri-bo-chay.scss',
})
export class QuanTriBoChayComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly boCuc = inject(BoCucTrang);
  protected readonly auth = inject(AuthService);

  public readonly trangThai = signal<TrangThaiBoChay | null>(null);
  public readonly dangTai = signal<boolean>(true);
  public readonly loi = signal<string | null>(null);

  public readonly cacChuKy = CAC_CHU_KY_TU_LAM_MOI;
  public readonly chuKyTuLamMoi = signal<number>(docChuKyDaLuu());
  /** Thoi diem nhan so lieu (ms) va dong ho moi giay de dem nguoc keep_alive tren trinh duyet. */
  private readonly thoiDiemNhan = signal<number | null>(null);
  private readonly bayGio = signal<number>(Date.now());

  public readonly nhanCapNhat = computed(() => {
    const luc = this.thoiDiemNhan();
    return luc === null ? null : DINH_DANG_GIO.format(luc);
  });

  public constructor() {
    const dongHo = setInterval(() => this.bayGio.set(Date.now()), 1000);
    let henGio: ReturnType<typeof setInterval> | null = null;

    // Lap lai theo chu ky da chon; tab dang an thi bo qua, quay lai thi lam moi ngay
    effect((onCleanup) => {
      const giay = this.chuKyTuLamMoi();
      if (giay <= 0) return;
      henGio = setInterval(() => {
        if (!document.hidden) this.taiDuLieu();
      }, giay * 1000);
      onCleanup(() => {
        if (henGio !== null) clearInterval(henGio);
      });
    });
    const khiHienLai = (): void => {
      if (!document.hidden && this.chuKyTuLamMoi() > 0) this.taiDuLieu();
    };
    document.addEventListener('visibilitychange', khiHienLai);

    inject(DestroyRef).onDestroy(() => {
      clearInterval(dongHo);
      if (henGio !== null) clearInterval(henGio);
      document.removeEventListener('visibilitychange', khiHienLai);
    });
  }

  public ngOnInit(): void {
    this.boCuc.datTieuDe(
      'Tình trạng bộ chạy',
      [{ nhan: 'Tình trạng bộ chạy', lienKet: null }],
      'Quản trị',
      'Theo dõi tài nguyên GPU, mô hình nạp và kiểm tra lệch ngữ cảnh',
    );
    this.taiDuLieu();
  }

  /** Lan dau hien vong xoay; cac lan lam moi sau giu nguyen bang so lieu de khong nhap nhay. */
  public taiDuLieu(): void {
    if (this.trangThai() === null) this.dangTai.set(true);
    this.api.layTrangThaiBoChay().subscribe({
      next: (res) => {
        this.trangThai.set(res);
        this.thoiDiemNhan.set(Date.now());
        this.bayGio.set(Date.now());
        this.loi.set(null);
        this.dangTai.set(false);
      },
      error: (err: Error) => {
        this.loi.set(err.message || 'Không thể kết nối máy chủ để lấy thông tin.');
        this.dangTai.set(false);
      },
    });
  }

  public chonChuKy(suKien: Event): void {
    const giay = Number((suKien.target as HTMLSelectElement).value);
    this.chuKyTuLamMoi.set(giay);
    try {
      localStorage.setItem(KHOA_LUU_CHU_KY, String(giay));
    } catch {
      // Trinh duyet chan luu tru: van dung chu ky trong phien hien tai
    }
  }

  /** So giay keep_alive con lai tai thoi diem hien tai, tru di thoi gian tu luc nhan so lieu. */
  public giayConLai(soGiayLucNhan: number | null | undefined): number | null {
    const luc = this.thoiDiemNhan();
    if (soGiayLucNhan === null || soGiayLucNhan === undefined || luc === null) return null;
    return soGiayLucNhan - (this.bayGio() - luc) / 1000;
  }

  public dinhDangVram(gb: number | null | undefined): string {
    if (gb === null || gb === undefined) {
      return '--';
    }
    return `${DINH_DANG_GB.format(gb)} GB`;
  }

  public dinhDangThoiGian(giay: number | null | undefined): string {
    if (giay === null || giay === undefined) {
      return 'Không xác định';
    }
    if (giay <= 0) {
      return 'Đã hết hạn';
    }
    const phut = Math.floor(giay / 60);
    const giayDu = Math.floor(giay % 60);
    if (phut > 0) {
      return `Còn ${phut}m ${giayDu}s`;
    }
    return `Còn ${giayDu}s`;
  }
}
