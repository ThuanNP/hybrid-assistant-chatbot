import {
  Component,
  DestroyRef,
  ElementRef,
  effect,
  afterNextRender,
  afterRenderEffect,
  computed,
  inject,
  input,
  output,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { BoCucTrang, MucDuongDan, TRANG_CHU } from '../../core/bo-cuc-trang';
import { CAU_HINH_APP } from '../../core/cau-hinh';
import { nhanBacLocal, nhanCheDoDinhTuyen, nhanHoSoGpu } from '../../core/nhan-hien-thi';
import { DichVuThongBao } from '../../core/thong-bao';
import { BieuTuongComponent } from '../bieu-tuong/bieu-tuong';

type BangThaXuong = 'he-thong' | 'thong-bao' | 'nguoi-dung';

/** Chu ky kiem tra /health cho nut trang thai "Dang hoat dong" (ms). */
const CHU_KY_KIEM_TRA_SUC_KHOE_MS = 30_000;

/**
 * Thanh dau trang dung chung (DESIGN.md muc 6.2): nut dong mo sidebar co dinh va breadcrumb
 * ben trai; tim kiem, thong bao va tai khoan ben phai. Tieu de trang nam rieng o vung noi dung.
 */
@Component({
  selector: 'app-thanh-dau-trang',
  imports: [RouterLink, RouterLinkActive, BieuTuongComponent],
  templateUrl: './thanh-dau-trang.html',
  styleUrl: './thanh-dau-trang.scss',
  host: {
    '(document:click)': 'dongBang()',
    '(document:keydown.escape)': 'dongBang()',
  },
})
export class ThanhDauTrangComponent {
  protected readonly boCuc = inject(BoCucTrang);
  protected readonly thongBao = inject(DichVuThongBao);
  protected readonly authService = inject(AuthService);

  public readonly trangChu = TRANG_CHU;
  public readonly nhanCheDo = nhanCheDoDinhTuyen;
  public readonly nhanGpu = nhanHoSoGpu;
  public readonly nhanBac = nhanBacLocal;

  /** Trang thai sidebar tu khung ung dung, dung cho `aria-expanded` cua nut dong mo. */
  public readonly sidebarMo = input(true);
  public readonly chuyenDoiSidebar = output<void>();

  public readonly tenNguoiDung = computed(() => {
    const nd = this.authService.nguoiDung();
    return nd?.ho_ten || nd?.email || 'Cán bộ nhân viên';
  });

  public readonly chucDanh = computed(() => {
    if (this.authService.laQuanTri()) return 'Quản trị viên';
    if (this.authService.laChiDoc()) return 'Chỉ đọc';
    return 'Chuyên viên';
  });

  public readonly phongBan = computed(() => {
    return this.authService.nguoiDung()?.phong_ban || 'Nội bộ';
  });

  public readonly donVi = CAU_HINH_APP.DON_VI;
  public readonly bangMo = signal<BangThaXuong | null>(null);

  public dangXuat(): void {
    this.dongBang();
    this.authService.dangXuat().subscribe();
  }

  private readonly khungDuongDan = viewChild.required<ElementRef<HTMLElement>>('khungDuongDan');
  private readonly doDuongDan = viewChild.required<ElementRef<HTMLElement>>('doDuongDan');

  /** Cac muc cha giua Trang chu va muc hien tai (co lien ket). */
  public readonly mucGiua = computed(() => this.boCuc.duongDan().filter((m) => m.lienKet !== null));
  /** Muc hien tai (cuoi breadcrumb, khong co lien ket). */
  public readonly mucCuoi = computed<MucDuongDan | null>(() => {
    const ds = this.boCuc.duongDan();
    const cuoi = ds.at(-1);
    return cuoi && cuoi.lienKet === null ? cuoi : null;
  });
  public readonly mucChaGanNhat = computed(() => this.mucGiua().at(-1) ?? null);
  public readonly nhanMucAn = computed(() => this.mucGiua().map((m) => m.nhan).join(' / '));

  /** Breadcrumb day du vuot qua be ngang cho phep thi gop cac muc giua thanh "…". */
  public readonly rutGonDuongDan = signal(false);

  public constructor() {
    // Moi truong khong co ResizeObserver (jsdom khi kiem thu) thi chi do khi duong dan doi
    const quanSat =
      typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => this.doLaiDuongDan());
    afterNextRender(() => quanSat?.observe(this.khungDuongDan().nativeElement));
    // Duong dan doi (sang man khac, doi tieu de hoi thoai) thi do lai sau khi ban do da ve xong
    afterRenderEffect(() => {
      this.boCuc.duongDan();
      untracked(() => this.doLaiDuongDan());
    });
    // Nut trang thai kiem tra lai /health moi CHU_KY_KIEM_TRA_SUC_KHOE_MS; tab an thi bo qua
    const henGioSucKhoe = setInterval(() => {
      if (!document.hidden) this.thongBao.kiemTraSucKhoe();
    }, CHU_KY_KIEM_TRA_SUC_KHOE_MS);
    const khiHienLai = (): void => {
      if (!document.hidden) this.thongBao.kiemTraSucKhoe();
    };
    document.addEventListener('visibilitychange', khiHienLai);
    inject(DestroyRef).onDestroy(() => {
      quanSat?.disconnect();
      clearInterval(henGioSucKhoe);
      document.removeEventListener('visibilitychange', khiHienLai);
    });
  }

  /** Nap lai trang thai he thong moi khi phien dang nhap duoc thiet lap (ke ca sau F5). */
  private readonly napKhiDangNhap = effect(() => {
    this.authService.daDangNhap();
    untracked(() => this.thongBao.taiLai());
  });

  private doLaiDuongDan(): void {
    const khung = this.khungDuongDan().nativeElement;
    if (khung.clientWidth === 0) return; // dang an (di dong)
    this.rutGonDuongDan.set(this.doDuongDan().nativeElement.scrollWidth > khung.clientWidth);
  }

  public chuyenBang(bang: BangThaXuong, suKien: Event): void {
    suKien.stopPropagation();
    const dangMo = this.bangMo() === bang;
    this.bangMo.set(dangMo ? null : bang);
    if (!dangMo && bang !== 'nguoi-dung') this.thongBao.taiLai();
  }

  public dongBang(): void {
    this.bangMo.set(null);
  }
}
