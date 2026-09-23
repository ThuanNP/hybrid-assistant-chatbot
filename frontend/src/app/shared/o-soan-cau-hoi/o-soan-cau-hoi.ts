import { Component, ElementRef, input, model, output, viewChild } from '@angular/core';
import { BieuTuongComponent } from '../bieu-tuong/bieu-tuong';

const CHIEU_CAO_TOI_DA_PX = 200;

/**
 * O soan cau hoi dung chung cho Trang chu va Tro chuyen (DESIGN.md muc 8.3):
 * Enter de gui, Shift + Enter xuong dong, tu gian toi da khoang 6 dong.
 */
@Component({
  selector: 'app-o-soan-cau-hoi',
  imports: [BieuTuongComponent],
  templateUrl: './o-soan-cau-hoi.html',
  styleUrl: './o-soan-cau-hoi.scss',
})
export class OSoanCauHoiComponent {
  private readonly vungNhap = viewChild<ElementRef<HTMLTextAreaElement>>('vungNhap');

  public readonly noiDung = model('');
  public readonly dangGui = input(false);
  public readonly thoiGianDemNguoc = input<number | null>(null);
  public readonly goiY = input('Nhập câu hỏi nghiệp vụ...');
  public readonly nhanTruyCap = input('Nhập câu hỏi nghiệp vụ');
  public readonly gui = output<string>();
  public readonly dung = output<void>();

  public batPhim(suKien: KeyboardEvent): void {
    if (suKien.key !== 'Enter' || suKien.shiftKey || suKien.isComposing) return;
    suKien.preventDefault();
    this.bamGui();
  }

  public bamGui(): void {
    const cauHoi = this.noiDung().trim();
    const demNguoc = this.thoiGianDemNguoc();
    if (!cauHoi || this.dangGui() || (demNguoc !== null && demNguoc > 0)) return;
    this.gui.emit(cauHoi);
    this.noiDung.set('');
    this.datLaiChieuCao();
  }

  public nhapLieu(suKien: Event): void {
    const el = suKien.target as HTMLTextAreaElement;
    this.noiDung.set(el.value);
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, CHIEU_CAO_TOI_DA_PX)}px`;
  }

  public datTieuDiem(): void {
    this.vungNhap()?.nativeElement.focus();
  }

  private datLaiChieuCao(): void {
    const el = this.vungNhap()?.nativeElement;
    if (el) el.style.height = 'auto';
  }
}
