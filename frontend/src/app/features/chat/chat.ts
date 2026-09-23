import { NgTemplateOutlet } from '@angular/common';
import {
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  computed,
  effect,
  inject,
  input,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { BoCucTrang } from '../../core/bo-cuc-trang';
import { KhoHoiThoai } from '../../core/kho-hoi-thoai';
import {
  ChiTietHoiThoai,
  Luot,
  SuKien,
  SuKienBatDau,
  SuKienHangDoi,
  SuKienLoi,
  SuKienManh,
  SuKienXong,
} from '../../core/mo-hinh';
import { nhanCheDoDinhTuyen } from '../../core/nhan-hien-thi';
import { SseService } from '../../core/sse.service';
import { DANH_SACH_TAC_VU_NHANH, TacVuNhanh } from '../../core/tac-vu-nhanh';
import { BieuTuongComponent } from '../../shared/bieu-tuong/bieu-tuong';
import { HuyHieuMoHinhComponent } from '../../shared/huy-hieu-mo-hinh/huy-hieu-mo-hinh';
import { OSoanCauHoiComponent } from '../../shared/o-soan-cau-hoi/o-soan-cau-hoi';
import { KhoiVanBan, phanTichVanBan } from './dinh-dang-van-ban';

export interface TinNhanHienThi {
  id: string | number;
  vaiTro: 'nguoi_dung' | 'tro_ly' | 'he_thong';
  noiDung: string;
  khoiVanBan: KhoiVanBan[];
  dangPhat?: boolean;
  coLoi?: boolean;
  thongDiepLoi?: string;
  maYeuCau?: string;
  nguon?: string;
  tang?: number;
  bacLocal?: string | null;
  model?: string;
  tokenVao?: number;
  tokenRa?: number;
  chiPhiUsd?: number;
  tocDoTokS?: number;
  doTreMs?: number;
  nhanAi?: string;
  daCatNguCanh?: boolean;
  soLuotBiCat?: number;
  /** Co ha_cap do may chu tinh; undefined khi may chu cu chua tra. */
  haCap?: boolean;
}

const MA_HOI_THOAI_MOI = 'moi';
const THOI_GIAN_BAO_NAP_MODEL_MS = 3000;
const KHOANG_CACH_COI_LA_CUOI_PX = 50;
const SO_DONG_CAU_HOI_DAI = 6;
const SO_KY_TU_CAU_HOI_DAI = 360;

/**
 * Man Tro chuyen (DESIGN.md muc 8): mot cot doc o giua, o soan co dinh o day.
 * Tuyen `/tro-chuyen/moi` la cuoc tro chuyen trong; khi may chu cap ma hoi thoai,
 * dia chi doi sang `/tro-chuyen/:id` ma khong tao lai thanh phan.
 */
@Component({
  selector: 'app-chat',
  imports: [
    NgTemplateOutlet,
    BieuTuongComponent,
    HuyHieuMoHinhComponent,
    OSoanCauHoiComponent,
  ],
  templateUrl: './chat.html',
  styleUrl: './chat.scss',
})
export class ChatComponent implements OnInit, OnDestroy {
  private readonly khungTinNhan = viewChild<ElementRef<HTMLElement>>('khungTinNhan');
  private readonly oSoan = viewChild(OSoanCauHoiComponent);

  private readonly sseService = inject(SseService);
  private readonly apiService = inject(ApiService);
  private readonly router = inject(Router);
  private readonly kho = inject(KhoHoiThoai);
  private readonly boCuc = inject(BoCucTrang);

  /** Tham so tuyen duong `:id`, gan tu dong nho `withComponentInputBinding`. */
  public readonly id = input<string>(MA_HOI_THOAI_MOI);

  public readonly danhSachTinNhan = signal<TinNhanHienThi[]>([]);
  public readonly hoiThoaiHienTaiId = signal<number | null>(null);
  public readonly noiDungNhap = signal<string>('');
  public readonly dangGui = signal<boolean>(false);
  public readonly dangTaiLichSu = signal<boolean>(false);
  public readonly loiTaiLichSu = signal<string | null>(null);
  public readonly thongTinHangDoi = signal<string | null>(null);
  public readonly thongBaoNapModel = signal<boolean>(false);
  public readonly dangOViTriCuoi = signal<boolean>(true);
  public readonly cheDoDinhTuyen = signal<string>('local_truoc');
  public readonly idDaSaoChep = signal<string | number | null>(null);
  public readonly thoiGianDemNguoc = signal<number | null>(null);
  /** Cac cau hoi dai nguoi dung da bam "Xem thêm". */
  private readonly cacIdMoRong = signal<ReadonlySet<string | number>>(new Set());

  public readonly cacTacVu = DANH_SACH_TAC_VU_NHANH;
  public readonly dangTrong = computed(
    () => this.danhSachTinNhan().length === 0 && !this.dangTaiLichSu(),
  );
  public readonly tieuDe = computed(() => {
    const id = this.hoiThoaiHienTaiId();
    if (id === null) return 'Cuộc trò chuyện mới';
    return this.kho.danhSach().find((ht) => ht.id === id)?.tieu_de ?? 'Cuộc trò chuyện';
  });

  private abortController: AbortController | null = null;
  private sseSubscription: Subscription | null = null;
  private timerNapModel: ReturnType<typeof setTimeout> | null = null;
  private timerDemNguoc: ReturnType<typeof setInterval> | null = null;
  private daNhanManhDauTien = false;

  constructor() {
    // Doi tuyen: mo hoi thoai da co hoac tro ve cuoc tro chuyen trong.
    effect(() => {
      const id = this.id();
      untracked(() => this.xuLyDoiTuyen(id));
    });

    // Tieu de hoi thoai va che do dinh tuyen hien tren thanh dau trang dung chung.
    effect(() => {
      const cheDo = this.cheDoDinhTuyen();
      const tieuDe = this.tieuDe();
      const duongDan =
        this.hoiThoaiHienTaiId() === null
          ? [{ nhan: tieuDe, lienKet: null }]
          : [
              { nhan: 'Lịch sử hội thoại', lienKet: '/lich-su' },
              { nhan: tieuDe, lienKet: null },
            ];
      this.boCuc.datTieuDe(tieuDe, duongDan, nhanCheDoDinhTuyen(cheDo));
    });

    // Yeu cau "Cuoc tro chuyen moi" tu sidebar hoac Trang chu, co the kem cau hoi dau tien.
    effect(() => {
      if (!this.kho.yeuCauMoi()) return;
      untracked(() => {
        const yeuCau = this.kho.nhanYeuCauMoi();
        this.batDauHoiThoaiMoi();
        if (yeuCau?.cauHoi) this.guiTinNhan(yeuCau.cauHoi);
      });
    });
  }

  public ngOnInit(): void {
    this.apiService.layModels().subscribe({
      next: (m) => {
        if (m?.che_do_dinh_tuyen) this.cheDoDinhTuyen.set(m.che_do_dinh_tuyen);
      },
      error: () => {},
    });
  }

  public ngOnDestroy(): void {
    this.huyStreaming();
    this.xoaHenGioNapModel();
    this.xoaTimerDemNguoc();
  }

  private xuLyDoiTuyen(id: string): void {
    if (id === MA_HOI_THOAI_MOI) {
      if (this.hoiThoaiHienTaiId() !== null) this.batDauHoiThoaiMoi();
      return;
    }
    const soId = Number(id);
    if (!Number.isInteger(soId) || soId <= 0) {
      void this.router.navigate(['/tro-chuyen', MA_HOI_THOAI_MOI], { replaceUrl: true });
      return;
    }
    if (soId !== this.hoiThoaiHienTaiId()) this.moHoiThoai(soId);
  }

  private moHoiThoai(id: number): void {
    this.dungPhat();
    this.hoiThoaiHienTaiId.set(id);
    this.danhSachTinNhan.set([]);
    this.loiTaiLichSu.set(null);
    this.dangTaiLichSu.set(true);
    this.apiService.layHoiThoai(id).subscribe({
      next: (ct: ChiTietHoiThoai) => {
        this.dangTaiLichSu.set(false);
        this.napLichSuHoiThoai(ct.cac_luot || []);
      },
      error: (loi: unknown) => {
        this.dangTaiLichSu.set(false);
        this.loiTaiLichSu.set(loi instanceof Error ? loi.message : 'Không thể mở hội thoại.');
      },
    });
  }

  public batDauHoiThoaiMoi(): void {
    this.dungPhat();
    this.hoiThoaiHienTaiId.set(null);
    this.danhSachTinNhan.set([]);
    this.loiTaiLichSu.set(null);
    setTimeout(() => this.oSoan()?.datTieuDiem(), 0);
  }

  /** Mo lai hoi thoai giu du huy hieu, nhan AI va dong luoc bot nhu luc dang phat. */
  private napLichSuHoiThoai(cacLuot: Luot[]): void {
    const danhSach = cacLuot.map((l) => ({
      id: l.id,
      vaiTro: l.vai_tro as 'nguoi_dung' | 'tro_ly' | 'he_thong',
      noiDung: l.noi_dung,
      khoiVanBan: phanTichVanBan(l.noi_dung),
      model: l.model_da_dung ?? undefined,
      nguon: l.nguon ?? undefined,
      tang: l.tang ?? 0,
      bacLocal: l.bac_local ?? undefined,
      tokenVao: l.token_vao ?? 0,
      tokenRa: l.token_ra ?? 0,
      chiPhiUsd: l.chi_phi_usd ?? 0,
      tocDoTokS: l.toc_do_tok_s ?? 0,
      doTreMs: l.do_tre_ms ?? 0,
      nhanAi: l.nhan_ai ?? undefined,
      maYeuCau: l.ma_yeu_cau ?? undefined,
      daCatNguCanh: l.da_cat_ngu_canh ?? false,
      soLuotBiCat: l.so_luot_bi_cat ?? 0,
      haCap: l.ha_cap,
    }));
    this.danhSachTinNhan.set(danhSach);
    this.cuonXuongDay(true);
  }

  public bamGoiY(tacVu: TacVuNhanh): void {
    this.guiTinNhan(tacVu.cauHoi);
  }

  public guiTinNhan(cauHoi: string = this.noiDungNhap()): void {
    const text = cauHoi.trim();
    const demNguoc = this.thoiGianDemNguoc();
    if (!text || this.dangGui() || (demNguoc !== null && demNguoc > 0)) return;

    this.themTinNhanNguoiDung(text);
    this.noiDungNhap.set('');

    const troLyId = `tro-ly-${Date.now()}`;
    this.themTinNhanTroLyRong(troLyId);
    this.khoiTaoTienTrinhGui(text, troLyId);
  }

  private themTinNhanNguoiDung(text: string): void {
    const tinNguoiDung: TinNhanHienThi = {
      id: `nd-${Date.now()}`,
      vaiTro: 'nguoi_dung',
      noiDung: text,
      khoiVanBan: phanTichVanBan(text),
    };
    this.danhSachTinNhan.update((ds) => [...ds, tinNguoiDung]);
    this.cuonXuongDay(true);
  }

  private themTinNhanTroLyRong(id: string): void {
    const tinTroLy: TinNhanHienThi = {
      id,
      vaiTro: 'tro_ly',
      noiDung: '',
      khoiVanBan: [],
      dangPhat: true,
    };
    this.danhSachTinNhan.update((ds) => [...ds, tinTroLy]);
  }

  private khoiTaoTienTrinhGui(text: string, troLyId: string): void {
    this.dangGui.set(true);
    this.thongTinHangDoi.set(null);
    this.thongBaoNapModel.set(false);
    this.daNhanManhDauTien = false;
    this.abortController = new AbortController();

    this.timerNapModel = setTimeout(() => {
      if (!this.daNhanManhDauTien && this.dangGui()) {
        this.thongBaoNapModel.set(true);
      }
    }, THOI_GIAN_BAO_NAP_MODEL_MS);

    const stream$ = this.sseService.guiTinNhan(
      text,
      this.hoiThoaiHienTaiId(),
      this.abortController.signal,
    );

    this.sseSubscription = stream$.subscribe({
      next: (sk) => this.xuLySuKienSse(sk, troLyId),
      error: (err: unknown) => this.xuLyLoiStream(err, troLyId),
      complete: () => this.ketThucGui(troLyId),
    });
  }

  public dungPhat(): void {
    this.huyStreaming();
    this.dangGui.set(false);
    this.thongTinHangDoi.set(null);
    this.thongBaoNapModel.set(false);
    this.xoaHenGioNapModel();
    this.danhSachTinNhan.update((ds) =>
      ds.map((tn) => (tn.dangPhat ? { ...tn, dangPhat: false } : tn)),
    );
  }

  private huyStreaming(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    if (this.sseSubscription) {
      this.sseSubscription.unsubscribe();
      this.sseSubscription = null;
    }
  }

  private xoaHenGioNapModel(): void {
    if (this.timerNapModel) {
      clearTimeout(this.timerNapModel);
      this.timerNapModel = null;
    }
  }

  private xuLySuKienSse(sk: SuKien, troLyId: string): void {
    switch (sk.loai) {
      case 'hang_doi':
        this.xuLyHangDoi(sk);
        break;
      case 'bat_dau':
        this.xuLyBatDau(sk, troLyId);
        break;
      case 'manh':
        this.xuLyManh(sk, troLyId);
        break;
      case 'xong':
        this.xuLyXong(sk, troLyId);
        break;
      case 'loi':
        this.xuLyLoi(sk, troLyId);
        break;
    }
  }

  private xuLyHangDoi(sk: SuKienHangDoi): void {
    // May chu tra so thuc (trung vi x vi tri); lam tron len giay cho de doc
    const thoiGian = sk.uoc_luong_giay
      ? `, dự kiến chờ khoảng ${Math.ceil(sk.uoc_luong_giay)} giây`
      : '';
    this.thongTinHangDoi.set(`Anh/Chị đang ở vị trí ${sk.vi_tri}${thoiGian}`);
  }

  private xuLyBatDau(sk: SuKienBatDau, troLyId: string): void {
    this.thongTinHangDoi.set(null);
    if (sk.hoi_thoai_id && !this.hoiThoaiHienTaiId()) {
      this.hoiThoaiHienTaiId.set(sk.hoi_thoai_id);
      void this.router.navigate(['/tro-chuyen', sk.hoi_thoai_id], { replaceUrl: true });
      this.kho.taiLai();
    }
    this.capNhatTinNhan(troLyId, (tn) => ({
      ...tn,
      nguon: sk.nguon,
      tang: sk.tang,
      model: sk.model,
      daCatNguCanh: sk.da_cat_ngu_canh,
      soLuotBiCat: sk.so_luot_bi_cat,
    }));
  }

  private xuLyManh(sk: SuKienManh, troLyId: string): void {
    if (!this.daNhanManhDauTien) {
      this.daNhanManhDauTien = true;
      this.thongBaoNapModel.set(false);
      this.xoaHenGioNapModel();
    }
    this.capNhatTinNhan(troLyId, (tn) => {
      const noiDungMoi = tn.noiDung + sk.noi_dung;
      return {
        ...tn,
        noiDung: noiDungMoi,
        khoiVanBan: phanTichVanBan(noiDungMoi),
      };
    });
    if (this.dangOViTriCuoi()) {
      this.cuonXuongDay();
    }
  }

  private xuLyXong(sk: SuKienXong, troLyId: string): void {
    this.thongTinHangDoi.set(null);
    this.capNhatTinNhan(troLyId, (tn) => ({
      ...tn,
      dangPhat: false,
      tokenVao: sk.token_vao,
      tokenRa: sk.token_ra,
      chiPhiUsd: sk.chi_phi_usd,
      tocDoTokS: sk.toc_do_tok_s,
      doTreMs: sk.do_tre_ms,
      nguon: sk.nguon,
      tang: sk.tang,
      bacLocal: sk.bac_local,
      model: sk.model,
      nhanAi: sk.nhan_ai,
      maYeuCau: sk.ma_yeu_cau || tn.maYeuCau,
      haCap: sk.ha_cap,
    }));
    this.kho.taiLai();
  }

  private xuLyLoi(sk: SuKienLoi, troLyId: string): void {
    if (sk.retry_after && sk.retry_after > 0) {
      this.batDauDemNguoc(sk.retry_after);
    }
    this.capNhatTinNhan(troLyId, (tn) => ({
      ...tn,
      dangPhat: false,
      coLoi: true,
      thongDiepLoi: sk.thong_diep,
      maYeuCau: sk.ma_yeu_cau,
    }));
  }

  private xuLyLoiStream(err: unknown, troLyId: string): void {
    if (typeof err === 'object' && err !== null && 'retryAfter' in err) {
      const retry = (err as { retryAfter?: number }).retryAfter;
      if (typeof retry === 'number' && retry > 0) {
        this.batDauDemNguoc(retry);
      }
    }
    const thongDiep = err instanceof Error ? err.message : 'Lỗi kết nối mạng';
    this.capNhatTinNhan(troLyId, (tn) => ({
      ...tn,
      dangPhat: false,
      coLoi: true,
      thongDiepLoi: thongDiep,
    }));
    this.ketThucGui(troLyId);
  }

  public batDauDemNguoc(soGiay: number): void {
    this.xoaTimerDemNguoc();
    this.thoiGianDemNguoc.set(soGiay);
    this.timerDemNguoc = setInterval(() => {
      const hienTai = this.thoiGianDemNguoc();
      if (hienTai === null || hienTai <= 1) {
        this.xoaTimerDemNguoc();
        this.thoiGianDemNguoc.set(null);
      } else {
        this.thoiGianDemNguoc.set(hienTai - 1);
      }
    }, 1000);
  }

  private xoaTimerDemNguoc(): void {
    if (this.timerDemNguoc) {
      clearInterval(this.timerDemNguoc);
      this.timerDemNguoc = null;
    }
  }

  private ketThucGui(troLyId: string): void {
    this.dangGui.set(false);
    this.thongTinHangDoi.set(null);
    this.thongBaoNapModel.set(false);
    this.xoaHenGioNapModel();
    this.capNhatTinNhan(troLyId, (tn) => ({ ...tn, dangPhat: false }));
  }

  private capNhatTinNhan(
    id: string | number,
    capNhat: (tn: TinNhanHienThi) => TinNhanHienThi,
  ): void {
    this.danhSachTinNhan.update((ds) => ds.map((tn) => (tn.id === id ? capNhat(tn) : tn)));
  }

  public onScroll(): void {
    const el = this.khungTinNhan()?.nativeElement;
    if (!el) return;
    const cachDay = el.scrollHeight - el.scrollTop - el.clientHeight;
    this.dangOViTriCuoi.set(cachDay < KHOANG_CACH_COI_LA_CUOI_PX);
  }

  public cuonXuongDay(cuongChe: boolean = false): void {
    if (!cuongChe && !this.dangOViTriCuoi()) return;
    setTimeout(() => {
      const el = this.khungTinNhan()?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    }, 0);
  }

  /** Cau hoi dai hon khoang 6 dong (theo so dong hoac do dai ky tu) thi thu gon. */
  public laCauHoiDai(noiDung: string): boolean {
    return (
      noiDung.length > SO_KY_TU_CAU_HOI_DAI || noiDung.split('\n').length > SO_DONG_CAU_HOI_DAI
    );
  }

  public daMoRong(id: string | number): boolean {
    return this.cacIdMoRong().has(id);
  }

  public chuyenMoRong(id: string | number): void {
    this.cacIdMoRong.update((cu) => {
      const moi = new Set(cu);
      if (moi.has(id)) moi.delete(id);
      else moi.add(id);
      return moi;
    });
  }

  public saoChepCauTraLoi(tn: TinNhanHienThi): void {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      void navigator.clipboard.writeText(tn.noiDung).then(() => {
        this.idDaSaoChep.set(tn.id);
        setTimeout(() => this.idDaSaoChep.set(null), 2000);
      });
    }
  }
}
