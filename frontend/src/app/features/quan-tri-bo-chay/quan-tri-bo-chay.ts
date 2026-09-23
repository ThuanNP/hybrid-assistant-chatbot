import { Component, OnInit, inject, signal } from '@angular/core';
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

/**
 * Trang quan tri tam thoi kiem tra tinh trang bo chay local (/quan-tri/bo-chay).
 * Danh rieng cho nguoi dung co vai tro quan_tri.
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

  public ngOnInit(): void {
    this.boCuc.datTieuDe(
      'Tình trạng bộ chạy',
      [{ nhan: 'Tình trạng bộ chạy', lienKet: null }],
      'Quản trị',
      'Theo dõi tài nguyên GPU, mô hình nạp và kiểm tra lệch ngữ cảnh',
    );
    this.taiDuLieu();
  }

  public taiDuLieu(): void {
    this.dangTai.set(true);
    this.loi.set(null);
    this.api.layTrangThaiBoChay().subscribe({
      next: (res) => {
        this.trangThai.set(res);
        this.dangTai.set(false);
      },
      error: (err: Error) => {
        this.loi.set(err.message || 'Không thể kết nối máy chủ để lấy thông tin.');
        this.dangTai.set(false);
      },
    });
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
    const giayDu = Math.round(giay % 60);
    if (phut > 0) {
      return `Còn ${phut}m ${giayDu}s`;
    }
    return `Còn ${giayDu}s`;
  }
}
