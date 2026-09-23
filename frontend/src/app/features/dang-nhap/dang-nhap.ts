/**
 * dang-nhap.ts - Component man hinh dang nhap cho he thong Tro ly noi bo.
 *
 * Tuan thu cac quy chuan:
 * - AGENTS.md: Dung dung nguyen trang man hinh Stitch da duyet.
 * - clean_code.md: Ham don nhiem < 40 dong, khong nuot ngoai le, xu ly loi day du.
 * - type_safety.md: Strict mode, khong dung any.
 */

import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { CAU_HINH_APP } from '../../core/cau-hinh';
import { DichVuThongBao } from '../../core/thong-bao';

@Component({
  selector: 'app-dang-nhap',
  imports: [CommonModule, FormsModule],
  templateUrl: './dang-nhap.html',
  styleUrl: './dang-nhap.scss',
})
export class DangNhapComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  /** Phien ban hien duoi form lay tu /health (khong can dang nhap), khong ghi cung. */
  protected readonly thongBao = inject(DichVuThongBao);

  public readonly email = signal('');
  public readonly matKhau = signal('');
  public readonly hienMatKhau = signal(false);
  public readonly dangXuLy = this.authService.dangXuLy;
  public readonly thongBaoLoi = signal<string | null>(null);
  public readonly maYeuCau = signal<string | null>(null);

  public readonly tieuDe = CAU_HINH_APP.TIEU_DE_HE_THONG;

  public constructor() {
    this.thongBao.taiLai();
  }

  public chuyenDoiHienMatKhau(): void {
    this.hienMatKhau.update((hien) => !hien);
  }

  public xuLyDangNhap(): void {
    const emailVal = this.email().trim();
    const matKhauVal = this.matKhau();

    if (!emailVal || !matKhauVal) {
      this.thongBaoLoi.set('Vui lòng nhập đầy đủ email và mật khẩu.');
      return;
    }

    this.thongBaoLoi.set(null);
    this.maYeuCau.set(null);

    this.authService.dangNhap(emailVal, matKhauVal).subscribe({
      next: () => {
        void this.router.navigate(['/']);
      },
      error: (err: unknown) => {
        this.xuLyLoiDangNhap(err);
      },
    });
  }

  private xuLyLoiDangNhap(err: unknown): void {
    let thongDiep = 'Đăng nhập không thành công. Vui lòng kiểm tra lại.';
    let maYc: string | null = null;

    if (typeof err === 'object' && err !== null) {
      const errObj = err as {
        error?: { loi?: { thong_diep?: string; ma_yeu_cau?: string }; detail?: string };
        status?: number;
      };
      if (errObj.error?.loi?.thong_diep) {
        thongDiep = errObj.error.loi.thong_diep;
        maYc = errObj.error.loi.ma_yeu_cau ?? null;
      } else if (typeof errObj.error?.detail === 'string') {
        thongDiep = errObj.error.detail;
      } else if (errObj.status === 401) {
        thongDiep = 'Email hoặc mật khẩu không chính xác.';
      } else if (errObj.status === 429) {
        thongDiep = 'Tài khoản đã đăng nhập sai quá nhiều lần. Vui lòng thử lại sau.';
      }
    }

    this.thongBaoLoi.set(thongDiep);
    this.maYeuCau.set(maYc);
  }
}
