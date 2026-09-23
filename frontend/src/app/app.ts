import { Component, DestroyRef, OnInit, computed, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  NavigationEnd,
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet,
} from '@angular/router';
import { filter } from 'rxjs';
import { AuthService } from './core/auth/auth.service';
import { BoCucTrang } from './core/bo-cuc-trang';
import { CAU_HINH_APP } from './core/cau-hinh';
import { KhoHoiThoai } from './core/kho-hoi-thoai';
import { DichVuThongBao } from './core/thong-bao';
import { BieuTuongComponent } from './shared/bieu-tuong/bieu-tuong';
import { ThanhDauTrangComponent } from './shared/thanh-dau-trang/thanh-dau-trang';

/**
 * Khung ung dung (DESIGN.md muc 6): sidebar va thanh dau trang dung chung cho moi man hinh,
 * vung noi dung chi hien thi dung mot man hinh theo tuyen duong.
 */
@Component({
  imports: [RouterOutlet, RouterLink, RouterLinkActive, BieuTuongComponent, ThanhDauTrangComponent],
  selector: 'app-root',
  host: { '(window:resize)': 'capNhatKichThuoc()' },
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App implements OnInit {
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly kho = inject(KhoHoiThoai);
  protected readonly boCuc = inject(BoCucTrang);
  protected readonly thongBao = inject(DichVuThongBao);
  protected readonly authService = inject(AuthService);

  public readonly tieuDe = signal<string>(CAU_HINH_APP.TIEU_DE_HE_THONG);
  public readonly tacGia = CAU_HINH_APP.TAC_GIA;
  public readonly namHienTai = new Date().getFullYear();
  /** Laptop man hinh nho (duoi 1100px) mac dinh thu gon sidebar de nhuong cho noi dung. */
  public readonly sidebarThuGon = signal(
    typeof window !== 'undefined' &&
      window.innerWidth >= CAU_HINH_APP.NGUONG_MOBILE_PX &&
      window.innerWidth < CAU_HINH_APP.NGUONG_THU_GON_SIDEBAR_PX,
  );
  public readonly drawerMo = signal(false);
  public readonly dangOTroChuyen = signal(false);
  public readonly dangODangNhap = signal(false);
  private readonly laDiDong = signal(this.laManHinhDiDong());

  /** Tu dong dong bo kho hoi thoai khi nguoi dung da dang nhap */
  private readonly dongBoKhoKhiDangNhap = effect(() => {
    if (this.authService.daDangNhap()) {
      this.kho.taiLai();
    }
  });

  /** Sidebar dang hien: tren di dong la ngan keo, tren may tinh la trang thai khong thu gon. */
  public readonly sidebarDangMo = computed(() =>
    this.laDiDong() ? this.drawerMo() : !this.sidebarThuGon(),
  );

  public capNhatKichThuoc(): void {
    this.laDiDong.set(this.laManHinhDiDong());
  }

  private laManHinhDiDong(): boolean {
    return typeof window !== 'undefined' && window.innerWidth < CAU_HINH_APP.NGUONG_MOBILE_PX;
  }

  public ngOnInit(): void {
    this.router.events
      .pipe(
        filter((suKien): suKien is NavigationEnd => suKien instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((suKien) => {
        this.dangOTroChuyen.set(suKien.urlAfterRedirects.startsWith('/tro-chuyen'));
        this.dangODangNhap.set(suKien.urlAfterRedirects.startsWith('/dang-nhap'));
        this.drawerMo.set(false);
      });
  }

  public chuyenDoiSidebar(): void {
    if (this.laManHinhDiDong()) {
      this.drawerMo.update((hienTai) => !hienTai);
      return;
    }
    this.sidebarThuGon.update((hienTai) => !hienTai);
  }

  public dongDrawer(): void {
    this.drawerMo.set(false);
  }

  public moHoiThoaiMoi(): void {
    this.drawerMo.set(false);
    this.kho.moHoiThoaiMoi();
  }
}
