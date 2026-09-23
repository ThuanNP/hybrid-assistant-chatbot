import {
  Component,
  ElementRef,
  afterRenderEffect,
  computed,
  effect,
  inject,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { BoCucTrang } from '../../core/bo-cuc-trang';
import { NhomThoiGian, dinhDangMocGon, xepNhomThoiGian } from '../../core/dinh-dang';
import { KhoHoiThoai } from '../../core/kho-hoi-thoai';
import { BoLocHoiThoai, HoiThoai, SapXepHoiThoai } from '../../core/mo-hinh';
import { BieuTuongComponent } from '../../shared/bieu-tuong/bieu-tuong';

export interface NhomHoiThoai {
  readonly ten: string;
  readonly cacMuc: HoiThoai[];
}

export const CAC_TUY_CHON_SAP_XEP: readonly { gia: SapXepHoiThoai; nhan: string }[] = [
  { gia: 'moi_nhat', nhan: 'Mới nhất' },
  { gia: 'cu_nhat', nhan: 'Cũ nhất' },
  { gia: 'ten_tang', nhan: 'Tên A → Z' },
  { gia: 'ten_giam', nhan: 'Tên Z → A' },
];

const THU_TU_NHOM: readonly NhomThoiGian[] = ['Hôm nay', 'Hôm qua', 'Cũ hơn'];
/** Tai trang ke tiep khi moc con cach day khung nhin chua toi 300px. */
const DO_CAO_TAI_TRUOC_PX = 300;
const KHOANG_TAI_TRUOC = `0px 0px ${DO_CAO_TAI_TRUOC_PX}px 0px`;
/** Cho nguoi dung go xong roi moi gui tu khoa len may chu. */
const THOI_GIAN_CHO_GO_MS = 300;

/**
 * Man Lich su hoi thoai: tra cuu, mo lai va xoa. Khong tro chuyen tai day; bam vao mot
 * muc se chuyen sang man Tro chuyen cua hoi thoai do. May chu loc, sap xep va dem ket qua;
 * man hinh chi xep nhom thoi gian tren cac trang da tai.
 */
@Component({
  selector: 'app-hoi-thoai',
  imports: [RouterLink, BieuTuongComponent],
  templateUrl: './hoi-thoai.html',
  styleUrl: './hoi-thoai.scss',
})
export class HoiThoaiComponent {
  private readonly boCuc = inject(BoCucTrang);
  private readonly kho = inject(KhoHoiThoai);
  /** Danh sach rieng co bo loc; sidebar va Trang chu van dung danh sach khong loc cua kho. */
  protected readonly ds = this.kho.taoDanhSachLoc();

  /** Noi dung o tim dang go; `tuKhoaDaChot` la gia tri da gui len may chu. */
  public readonly tuKhoa = signal('');
  private readonly tuKhoaDaChot = signal('');
  public readonly hoiThoaiDangXoa = signal<HoiThoai | null>(null);
  public readonly dangThucHienXoa = signal(false);
  public readonly loiXoa = signal<string | null>(null);

  public readonly sapXep = signal<SapXepHoiThoai>('moi_nhat');
  public readonly cacTuyChonSapXep = CAC_TUY_CHON_SAP_XEP;
  /** Nhan cua thu tu dang chon, hien trong chip (select that trong suot phu len tren). */
  public readonly nhanSapXep = computed(
    () => CAC_TUY_CHON_SAP_XEP.find((t) => t.gia === this.sapXep())?.nhan ?? '',
  );

  /** Bo loc da chot gui len may chu; doi bo loc thi tai lai tu trang 1. */
  public readonly boLoc = computed<BoLocHoiThoai>(() => ({
    tuKhoa: this.tuKhoaDaChot(),
    sapXep: this.sapXep(),
  }));

  public readonly dangLoc = computed(
    () => this.tuKhoaDaChot() !== '' || this.sapXep() !== 'moi_nhat',
  );

  /** Enter hoac nut Tim: gui tu khoa ngay, khong cho het thoi gian go; cung tu khoa thi tai lai. */
  public timLai(): void {
    const tuKhoa = this.tuKhoa().trim();
    if (tuKhoa === this.tuKhoaDaChot()) {
      this.ds.taiLai(this.boLoc());
      return;
    }
    this.tuKhoaDaChot.set(tuKhoa);
  }

  public xoaBoLoc(): void {
    this.tuKhoa.set('');
    this.tuKhoaDaChot.set('');
    this.sapXep.set('moi_nhat');
  }

  /** May chu da sap xep; sap theo ngay thi nhom theo moc thoi gian, theo ten thi mot danh sach phang. */
  public readonly cacNhom = computed<NhomHoiThoai[]>(() => {
    const ds = this.ds.danhSach();
    const kieu = this.sapXep();
    if (kieu === 'ten_tang' || kieu === 'ten_giam') {
      return ds.length ? [{ ten: kieu === 'ten_tang' ? 'Theo tên A → Z' : 'Theo tên Z → A', cacMuc: ds }] : [];
    }
    const bayGio = new Date();
    const theoNhom = new Map<NhomThoiGian, HoiThoai[]>();
    for (const ht of ds) {
      const nhom = xepNhomThoiGian(ht.cap_nhat_luc || ht.tao_luc, bayGio);
      theoNhom.set(nhom, [...(theoNhom.get(nhom) ?? []), ht]);
    }
    const thuTu = kieu === 'cu_nhat' ? [...THU_TU_NHOM].reverse() : THU_TU_NHOM;
    return thuTu.filter((ten) => theoNhom.has(ten)).map((ten) => ({
      ten,
      cacMuc: theoNhom.get(ten) ?? [],
    }));
  });

  private readonly mocTaiThem = viewChild<ElementRef<HTMLElement>>('mocTaiThem');

  constructor() {
    // Go xong moi chot tu khoa, tranh goi may chu sau tung phim.
    effect((onCleanup) => {
      const tuKhoa = this.tuKhoa().trim();
      const hen = setTimeout(() => this.tuKhoaDaChot.set(tuKhoa), THOI_GIAN_CHO_GO_MS);
      onCleanup(() => clearTimeout(hen));
    });

    // Tai trang dau khi mo man hinh va moi khi bo loc da chot thay doi.
    effect(() => {
      const boLoc = this.boLoc();
      untracked(() => this.ds.taiLai(boLoc));
    });

    // Cuon vo han: theo doi moc cuoi danh sach, gan het khung nhin thi tai trang ke tiep.
    effect((onCleanup) => {
      const moc = this.mocTaiThem()?.nativeElement;
      if (!moc || typeof IntersectionObserver === 'undefined') return;
      const theoDoi = new IntersectionObserver(
        (cacMuc) => {
          if (cacMuc.some((muc) => muc.isIntersecting)) this.ds.taiThem();
        },
        { rootMargin: KHOANG_TAI_TRUOC },
      );
      theoDoi.observe(moc);
      onCleanup(() => theoDoi.disconnect());
    });

    // Sau moi lan render, neu moc van nam trong khung nhin (trang dau chua lap day man hinh)
    // thi tai tiep, vi IntersectionObserver khong bao lai khi trang thai khong doi.
    afterRenderEffect(() => {
      if (this.ds.dangTaiThem() || this.ds.dangTai() || !this.ds.conThem()) return;
      const moc = this.mocTaiThem()?.nativeElement;
      if (!moc) return;
      if (moc.getBoundingClientRect().top < window.innerHeight + DO_CAO_TAI_TRUOC_PX) {
        untracked(() => this.ds.taiThem());
      }
    });

    // Dong mo ta (DESIGN.md muc 6.4a): binh thuong la cau huong dan co dinh, khong ghi tong so;
    // chi khi dang tim, loc moi ghi so ket qua de xac nhan bo loc co tac dung.
    effect(() => {
      this.boCuc.datTieuDe(
        'Lịch sử hội thoại',
        [{ nhan: 'Lịch sử hội thoại', lienKet: null }],
        null,
        this.moTaTrang(),
      );
    });
  }

  /** `tong_so` do may chu dem theo bo loc nen dung ngay tu trang dau. */
  public readonly moTaTrang = computed(() =>
    this.dangLoc()
      ? `Tìm thấy ${this.ds.tongSo()} cuộc trò chuyện`
      : 'Tìm và mở lại các cuộc trò chuyện trước đây',
  );

  public nhapTuKhoa(suKien: Event): void {
    this.tuKhoa.set((suKien.target as HTMLInputElement).value);
  }

  /** Mo hop thoai xac nhan xoa cua ung dung (khong dung window.confirm). */
  public moXacNhanXoa(ht: HoiThoai, suKien: Event): void {
    suKien.preventDefault();
    suKien.stopPropagation();
    this.loiXoa.set(null);
    this.hoiThoaiDangXoa.set(ht);
  }

  public dongXacNhanXoa(): void {
    if (this.dangThucHienXoa()) return;
    this.hoiThoaiDangXoa.set(null);
  }

  public thucHienXoa(): void {
    const ht = this.hoiThoaiDangXoa();
    if (!ht) return;

    this.dangThucHienXoa.set(true);
    this.kho.xoa(ht.id).subscribe({
      next: () => {
        this.ds.boMuc(ht.id);
        this.dangThucHienXoa.set(false);
        this.hoiThoaiDangXoa.set(null);
      },
      error: (loi: unknown) => {
        this.loiXoa.set(loi instanceof Error ? loi.message : 'Xoá hội thoại thất bại.');
        this.dangThucHienXoa.set(false);
        this.hoiThoaiDangXoa.set(null);
      },
    });
  }

  /** Dong phu cua moi muc theo ban thiet ke: `8 lượt · cập nhật 14:30`. */
  public moTaMuc(ht: HoiThoai): string {
    const moc = dinhDangMocGon(ht.cap_nhat_luc || ht.tao_luc, new Date());
    return ht.so_luot === undefined ? `Cập nhật ${moc}` : `${ht.so_luot} lượt · cập nhật ${moc}`;
  }
}
