import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HuyHieuMoHinhComponent } from './huy-hieu-mo-hinh';

describe('HuyHieuMoHinhComponent', () => {
  let component: HuyHieuMoHinhComponent;
  let fixture: ComponentFixture<HuyHieuMoHinhComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HuyHieuMoHinhComponent],
      providers: [provideZonelessChangeDetection()],
    }).compileComponents();

    fixture = TestBed.createComponent(HuyHieuMoHinhComponent);
    component = fixture.componentInstance;
  });

  it('nên khởi tạo thành công', () => {
    expect(component).toBeTruthy();
  });

  it('không có viền vàng khi tang = 0 và bac_local = chinh', async () => {
    fixture.componentRef.setInput('tang', 0);
    fixture.componentRef.setInput('bacLocal', 'chinh');
    fixture.componentRef.setInput('model', 'qwen3.5:9b-q4_K_M');
    await fixture.whenStable();

    expect(component.laRoiTangHoacHaCap()).toBe(false);
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.huy-hieu-container')?.classList.contains('canh-bao-roi-tang')).toBe(
      false,
    );
  });

  it('có viền vàng khi tang !== 0 (rơi tầng đám mây)', async () => {
    fixture.componentRef.setInput('tang', 1);
    fixture.componentRef.setInput('model', 'gemini-2.5-flash');
    await fixture.whenStable();

    expect(component.laRoiTangHoacHaCap()).toBe(true);
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.huy-hieu-container')?.classList.contains('canh-bao-roi-tang')).toBe(
      true,
    );
  });

  it('có viền vàng khi bac_local = nho hoặc 2 (hạ cấp local)', async () => {
    fixture.componentRef.setInput('tang', 0);
    fixture.componentRef.setInput('bacLocal', 'nho');
    fixture.componentRef.setInput('model', 'qwen3.5:4b-q4_K_M');
    await fixture.whenStable();

    expect(component.laRoiTangHoacHaCap()).toBe(true);
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.huy-hieu-container')?.classList.contains('canh-bao-roi-tang')).toBe(
      true,
    );
  });

  it('ẩn chi phí khi bằng 0', async () => {
    fixture.componentRef.setInput('chiPhiUsd', 0);
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.thong-so-chi-phi')).toBeNull();
  });

  it('hiển thị chi phí khi lớn hơn 0', async () => {
    fixture.componentRef.setInput('chiPhiUsd', 0.0012);
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.thong-so-chi-phi')?.textContent).toContain('0,0012 USD');
  });

  it('dòng hiển thị gọn: nhãn tiếng Việt, ẩn tốc độ và độ trễ bằng 0, tooltip giữ đủ thông số', async () => {
    fixture.componentRef.setInput('tang', 0);
    fixture.componentRef.setInput('bacLocal', 'nho');
    fixture.componentRef.setInput('model', 'qwen3.5:4b-q4_K_M');
    fixture.componentRef.setInput('tocDoTokS', 0);
    fixture.componentRef.setInput('doTreMs', 0);
    await fixture.whenStable();

    const khung = (fixture.nativeElement as HTMLElement).querySelector('.huy-hieu-container');
    expect(khung?.textContent).toContain('Nội bộ · nhỏ');
    expect(khung?.textContent).not.toContain('tok/s');
    expect(khung?.textContent).not.toContain('ms');
    expect(khung?.getAttribute('title')).toContain('Tốc độ: 0 tok/s');
  });

  it('ưu tiên cờ ha_cap của máy chủ: tầng 1 ở chế độ đám mây trước không bị cảnh báo', async () => {
    fixture.componentRef.setInput('tang', 1);
    fixture.componentRef.setInput('haCap', false);
    await fixture.whenStable();
    expect(component.laRoiTangHoacHaCap()).toBe(false);

    fixture.componentRef.setInput('tang', 0);
    fixture.componentRef.setInput('bacLocal', 'chinh');
    fixture.componentRef.setInput('haCap', true);
    await fixture.whenStable();
    expect(component.laRoiTangHoacHaCap()).toBe(true);
  });
});
