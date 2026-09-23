/**
 * sse.service.spec.ts - Kiem thu don vi cho SseService bang Vitest va ReadableStream gia.
 * Tuan thu cac quy chuan:
 * - AGENTS.md: Kiem thu cac tinh huong parse SSE, header Retry-After, huy qua AbortSignal.
 * - clean_code.md: Ham ngan gon, ro rang, khong lap ma.
 * - type_safety.md: Strict mode, khong su dung kieu any.
 */

import { provideZonelessChangeDetection, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthService } from './auth/auth.service';
import { SuKien } from './mo-hinh';
import { SseService } from './sse.service';

/**
 * Tao ReadableStream gia tu danh sach cac chuoi van ban nhi phan.
 */
function taoReadableStreamGia(cacKhoi: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const khoi of cacKhoi) {
        controller.enqueue(encoder.encode(khoi));
      }
      controller.close();
    },
  });
}

describe('SseService', () => {
  let service: SseService;
  const mockAuthService = {
    accessToken: signal<string | null>('fake-access-token'),
    lamMoiToken: vi.fn().mockReturnValue(of(null)),
  };

  beforeEach(() => {
    mockAuthService.accessToken.set('fake-access-token');
    mockAuthService.lamMoiToken.mockReset();
    mockAuthService.lamMoiToken.mockReturnValue(of(null));

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthService, useValue: mockAuthService },
        SseService,
      ],
    });
    service = TestBed.inject(SseService);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('tách đúng ba sự kiện nằm trong một khối dữ liệu', async () => {
    const duLieuKhoi =
      'event: bat_dau\n' +
      'data: {"hoi_thoai_id": 1, "nguon": "local", "tang": 0, "model": "qwen", "da_cat_ngu_canh": false, "so_luot_bi_cat": 0}\n\n' +
      'event: manh\n' +
      'data: {"noi_dung": "Xin chào Trợ lý"}\n\n' +
      'event: xong\n' +
      'data: {"token_vao": 10, "token_ra": 5, "chi_phi_usd": 0.0, "toc_do_tok_s": 25.0, "do_tre_ms": 120.0, "nguon": "local", "tang": 0, "model": "qwen", "nhan_ai": "Nội dung do AI tạo"}\n\n';

    const stream = taoReadableStreamGia([duLieuKhoi]);
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    );

    const danhSachSuKien: SuKien[] = [];
    await new Promise<void>((resolve, reject) => {
      service.guiTinNhan('Xin chào', 1).subscribe({
        next: (sk) => danhSachSuKien.push(sk),
        error: reject,
        complete: resolve,
      });
    });

    expect(danhSachSuKien.length).toBe(3);
    expect(danhSachSuKien[0].loai).toBe('bat_dau');
    expect(danhSachSuKien[1].loai).toBe('manh');
    if (danhSachSuKien[1].loai === 'manh') {
      expect(danhSachSuKien[1].noi_dung).toBe('Xin chào Trợ lý');
    }
    expect(danhSachSuKien[2].loai).toBe('xong');
  });

  it('ghép đúng một sự kiện bị cắt đôi giữa hai khối', async () => {
    const haiKhoi = ['event: manh\ndata: {"noi_du', 'ng": "Dữ liệu được ghép hoàn chỉnh"}\n\n'];

    const stream = taoReadableStreamGia(haiKhoi);
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    );

    const danhSachSuKien: SuKien[] = [];
    await new Promise<void>((resolve, reject) => {
      service.guiTinNhan('Kiểm tra ghép', 1).subscribe({
        next: (sk) => danhSachSuKien.push(sk),
        error: reject,
        complete: resolve,
      });
    });

    expect(danhSachSuKien.length).toBe(1);
    expect(danhSachSuKien[0].loai).toBe('manh');
    if (danhSachSuKien[0].loai === 'manh') {
      expect(danhSachSuKien[0].noi_dung).toBe('Dữ liệu được ghép hoàn chỉnh');
    }
  });

  it('bỏ qua dòng ": ping"', async () => {
    const duLieuKemPing = [
      ': ping\n\n' + 'event: manh\ndata: {"noi_dung": "Dữ liệu hữu ích"}\n\n' + ': ping\n\n',
    ];

    const stream = taoReadableStreamGia(duLieuKemPing);
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    );

    const danhSachSuKien: SuKien[] = [];
    await new Promise<void>((resolve, reject) => {
      service.guiTinNhan('Kiểm tra ping', 1).subscribe({
        next: (sk) => danhSachSuKien.push(sk),
        error: reject,
        complete: resolve,
      });
    });

    expect(danhSachSuKien.length).toBe(1);
    expect(danhSachSuKien[0].loai).toBe('manh');
    if (danhSachSuKien[0].loai === 'manh') {
      expect(danhSachSuKien[0].noi_dung).toBe('Dữ liệu hữu ích');
    }
  });

  it('phản hồi 429 phát SuKienLoi có thông điệp máy chủ', async () => {
    const loiBody = JSON.stringify({
      loi: {
        ma: 'QUA_HAN_MUC',
        thong_diep: 'Bạn đã gửi quá nhiều yêu cầu trong thời gian ngắn.',
        ma_yeu_cau: 'req-429-test',
      },
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(loiBody, {
        status: 429,
        headers: {
          'Content-Type': 'application/json',
          'Retry-After': '45',
          'X-Ma-Yeu-Cau': 'req-429-test',
        },
      }),
    );

    const danhSachSuKien: SuKien[] = [];
    await new Promise<void>((resolve, reject) => {
      service.guiTinNhan('Yêu cầu bị 429', 1).subscribe({
        next: (sk) => danhSachSuKien.push(sk),
        error: reject,
        complete: resolve,
      });
    });

    expect(danhSachSuKien.length).toBe(1);
    const suKien = danhSachSuKien[0];
    expect(suKien.loai).toBe('loi');
    if (suKien.loai === 'loi') {
      expect(suKien.ma).toBe('QUA_HAN_MUC');
      expect(suKien.thong_diep).toContain('Bạn đã gửi quá nhiều yêu cầu');
      expect(suKien.thong_diep).toContain('45');
      expect(suKien.ma_yeu_cau).toBe('req-429-test');
    }
  });

  it('abort thì dừng mà không phát SuKienLoi', async () => {
    const abortController = new AbortController();
    const encoder = new TextEncoder();

    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode('event: manh\ndata: {"noi_dung": "Mảnh trước khi dừng"}\n\n'),
        );
      },
      cancel() {
        // Dong reader khi bi huy
      },
    });

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    );

    const danhSachSuKien: SuKien[] = [];
    let daPhatLoi = false;

    await new Promise<void>((resolve) => {
      service.guiTinNhan('Thử nghiệm abort', 1, abortController.signal).subscribe({
        next: (sk) => {
          danhSachSuKien.push(sk);
          // Kích hoạt abort ngay khi nhận được sự kiện
          abortController.abort();
        },
        error: () => {
          daPhatLoi = true;
          resolve();
        },
        complete: () => {
          resolve();
        },
      });
    });

    expect(daPhatLoi).toBe(false);
    const coSuKienLoi = danhSachSuKien.some((sk) => sk.loai === 'loi');
    expect(coSuKienLoi).toBe(false);
    expect(danhSachSuKien.length).toBeGreaterThanOrEqual(1);
  });
});
