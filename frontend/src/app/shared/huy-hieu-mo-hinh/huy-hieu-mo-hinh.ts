import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

const DINH_DANG_USD = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 4 });
const DINH_DANG_GIAY = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 });
/** So nguyen va so thap phan kieu Viet Nam: 1.070 token, 52,9 tok/s. */
const DINH_DANG_SO = new Intl.NumberFormat('vi-VN');
const DINH_DANG_TOC_DO = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 });

@Component({
  selector: 'app-huy-hieu-mo-hinh',
  standalone: true,
  templateUrl: './huy-hieu-mo-hinh.html',
  styleUrl: './huy-hieu-mo-hinh.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuyHieuMoHinhComponent {
  public readonly nguon = input<string>('local');
  public readonly tang = input<number>(0);
  public readonly bacLocal = input<string | number | null>(null);
  public readonly model = input<string>('');
  public readonly tokenVao = input<number>(0);
  public readonly tokenRa = input<number>(0);
  public readonly chiPhiUsd = input<number>(0);
  public readonly tocDoTokS = input<number>(0);
  public readonly doTreMs = input<number>(0);
  public readonly maYeuCau = input<string>('');
  /** Hien "Da sao chep ma" trong 2 giay sau khi bam chip ma yeu cau. */
  public readonly daSaoChep = signal(false);
  /**
   * Co ha_cap do may chu tinh theo chuoi dinh tuyen thuc te cua nguoi dung: tang phuc vu khac
   * tang dau cua chuoi, hoac bac nho tra loi. `null` khi may chu cu chua tra truong nay.
   */
  public readonly haCap = input<boolean | null>(null);

  /**
   * Mau canh bao khi ha cap hoac roi tang. Uu tien co ha_cap cua may chu (dung ca voi che do
   * dam_may_truoc); thieu co thi suy ra tu tang !== 0 hoac bac nho.
   */
  public readonly laRoiTangHoacHaCap = computed<boolean>(() => {
    const haCap = this.haCap();
    if (haCap !== null) return haCap;
    const bacVal = this.bacLocal();
    const laHaCapLocal = bacVal === 'nho' || bacVal === '2' || bacVal === 2;
    return this.tang() !== 0 || laHaCapLocal;
  });

  /**
   * Nhãn tầng và nguồn hiển thị trên huy hiệu.
   */
  public readonly nhanNguonTang = computed<string>(() => {
    const tangVal = this.tang();
    const bacVal = this.bacLocal();
    if (tangVal === 0) {
      const tenBac = bacVal === 'nho' || bacVal === '2' || bacVal === 2 ? 'nhỏ' : 'chính';
      return `Nội bộ · ${tenBac}`;
    }
    return `Đám mây · tầng ${tangVal}`;
  });

  public readonly chuoiChiPhi = computed(() => `${DINH_DANG_USD.format(this.chiPhiUsd())} USD`);
  public readonly chuoiToken = computed(
    () => `${DINH_DANG_SO.format(this.tokenVao())}/${DINH_DANG_SO.format(this.tokenRa())} token`,
  );
  public readonly chuoiTocDo = computed(() => `${DINH_DANG_TOC_DO.format(this.tocDoTokS())} tok/s`);

  /** Mo ta day du cho tooltip va trinh doc man hinh; dong hien thi chi giu thong so khac 0. */
  public readonly moTaDayDu = computed(() =>
    [
      `Nguồn: ${this.nhanNguonTang()}`,
      `Mô hình: ${this.model()}`,
      `Token vào/ra: ${this.tokenVao()}/${this.tokenRa()}`,
      `Chi phí: ${this.chuoiChiPhi()}`,
      `Tốc độ: ${this.tocDoTokS()} tok/s`,
      `Độ trễ: ${this.chuoiDoTre()}`,
    ].join(' · '),
  );

  /**
   * Định dạng độ trễ hiển thị (ms hoặc s).
   */
  public readonly chuoiDoTre = computed<string>(() => {
    const ms = this.doTreMs();
    if (ms >= 1000) {
      return `${DINH_DANG_GIAY.format(ms / 1000)} s`;
    }
    return `${Math.round(ms)} ms`;
  });

  /**
   * Sao chép mã yêu cầu hoặc thông số vào clipboard.
   */
  public saoChepThongSo(): void {
    const ma = this.maYeuCau();
    const thongSo = `Model: ${this.model()}, Tầng: ${this.tang()}, Token: ${this.tokenVao()}/${this.tokenRa()}, Mã yêu cầu: ${ma}`;
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      void navigator.clipboard.writeText(ma || thongSo).then(() => {
        this.daSaoChep.set(true);
        setTimeout(() => this.daSaoChep.set(false), 2000);
      });
    }
  }
}
