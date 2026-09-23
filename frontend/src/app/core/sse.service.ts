/**
 * sse.service.ts - Dich vu tiep nhan dong su kien Server-Sent Events (SSE).
 * Tuan thu cac quy chuan:
 * - AGENTS.md: Mop chat phat theo dong SSE qua POST /api/v1/chat/stream.
 * - clean_code.md: Ham duoi 40 dong, don nhiem, khong nuot ngoai le, chu thich ro rang.
 * - type_safety.md: Strict mode, khong su dung kieu any.
 *
 * GIAI THICH VI SAO KHONG DUNG EventSource:
 * API EventSource mac dinh cua trinh duyet chi ho tro duy nhat phuong thuc HTTP GET,
 * khong the gui phuong thuc POST voi noi dung body JSON { noi_dung, hoi_thoai_id },
 * dong thoi khong cho phep them cac tieu de HTTP tuy bien.
 * Viec su dung fetch() ket hop ReadableStream va TextDecoder({ stream: true }) giup:
 * 1. Gui POST request mang tai JSON va headers text/event-stream chuan xac.
 * 2. Doc tung manh nhi phan ngay khi ve mang, khong bi nghen bo dem proxy.
 * 3. Chu dong huy bo ket noi qua AbortController (nut Dung) va dong reader sach se.
 * 4. Xu ly toan dien ma loi HTTP (401, 429 kem Retry-After, 503) voi noi dung JSON may chu.
 */

import { inject, Injectable } from '@angular/core';
import { firstValueFrom, Observable } from 'rxjs';
import { AuthService } from './auth/auth.service';
import { ENDPOINTS } from './cau-hinh';
import { SuKien, SuKienBatDau, SuKienHangDoi, SuKienLoi, SuKienManh, SuKienXong } from './mo-hinh';

@Injectable({
  providedIn: 'root',
})
export class SseService {
  private readonly authService = inject(AuthService);

  /**
   * Tao headers gui len SSE stream kem tieu de xac thuc va ma yeu cau.
   */
  private taoHeaders(token?: string | null): Record<string, string> {
    const maYeuCau =
      typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : `yc-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      'X-Ma-Yeu-Cau': maYeuCau,
    };
    const tok = token ?? this.authService.accessToken();
    if (tok) {
      headers['Authorization'] = `Bearer ${tok}`;
    }
    return headers;
  }

  /**
   * Gui yeu cau POST fetch den may chu.
   */
  private async guiYeuCauFetch(
    noiDung: string,
    hoiThoaiId: number | null | undefined,
    signal: AbortSignal,
    token?: string | null,
  ): Promise<Response> {
    return fetch(ENDPOINTS.CHAT_STREAM, {
      method: 'POST',
      headers: this.taoHeaders(token),
      credentials: 'include',
      body: JSON.stringify({
        noi_dung: noiDung,
        hoi_thoai_id: hoiThoaiId ?? null,
      }),
      signal,
    });
  }

  /**
   * Gui tin nhan chat theo dong SSE va tra ve luong cac SuKien phan biet bang truong `loai`.
   *
   * @param noiDung Noi dung cau hoi cua nguoi dung
   * @param hoiThoaiId ID cuoc hoi thoai hien tai (neu co)
   * @param signal AbortSignal ben ngoai de chu dong ngat luong khi can
   */
  public guiTinNhan(
    noiDung: string,
    hoiThoaiId?: number | null,
    signal?: AbortSignal,
  ): Observable<SuKien> {
    return new Observable<SuKien>((observer) => {
      const controller = new AbortController();
      let daHuy = false;

      const onExternalAbort = () => {
        daHuy = true;
        controller.abort();
      };

      if (signal?.aborted) {
        observer.complete();
        return;
      }
      signal?.addEventListener('abort', onExternalAbort, { once: true });

      const thucThi = async () => {
        let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
        const onAbortHuy = () => {
          daHuy = true;
          if (reader) {
            void reader.cancel().catch(() => {});
          }
        };
        controller.signal.addEventListener('abort', onAbortHuy, { once: true });

        try {
          let phanHoi = await this.guiYeuCauFetch(noiDung, hoiThoaiId, controller.signal);

          // Thu lam moi token mot lan neu bi loi 401
          if (phanHoi.status === 401) {
            const tokenMoi = await firstValueFrom(this.authService.lamMoiToken());
            if (tokenMoi) {
              phanHoi = await this.guiYeuCauFetch(noiDung, hoiThoaiId, controller.signal, tokenMoi);
            }
          }

          if (!phanHoi.ok) {
            const suKienLoi = await this.xuLyPhanHoiLoi(phanHoi);
            observer.next(suKienLoi);
            observer.complete();
            return;
          }

          reader = phanHoi.body?.getReader();
          if (!reader) {
            observer.next(
              this.taoSuKienLoiClient('KHONG_THE_DOC_STREAM', 'Khong the khoi tao bo doc stream'),
            );
            observer.complete();
            return;
          }

          await this.docVaPhanTichDong(reader, controller.signal, signal, (sk) =>
            observer.next(sk),
          );
          observer.complete();
        } catch (err: unknown) {
          await this.xuLyNgoaiLe(
            err,
            daHuy,
            controller.signal.aborted,
            signal?.aborted,
            reader,
            observer,
          );
        } finally {
          signal?.removeEventListener('abort', onExternalAbort);
          controller.signal.removeEventListener('abort', onAbortHuy);
        }
      };

      void thucThi();

      return () => {
        daHuy = true;
        signal?.removeEventListener('abort', onExternalAbort);
        controller.abort();
      };
    });
  }

  /**
   * Doc dong du lieu nhi phan tu reader, giai ma va phan tach cac khoi su kien SSE.
   */
  private async docVaPhanTichDong(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    controllerSignal: AbortSignal,
    externalSignal: AbortSignal | undefined,
    phatSuKien: (sk: SuKien) => void,
  ): Promise<void> {
    const decoder = new TextDecoder('utf-8');
    let boDem = '';

    while (true) {
      if (controllerSignal.aborted || externalSignal?.aborted) {
        break;
      }

      const { done, value } = await reader.read();
      if (done || controllerSignal.aborted || externalSignal?.aborted) {
        break;
      }

      boDem += decoder.decode(value, { stream: true });
      const cacKhoi = boDem.split(/\r?\n\r?\n/);
      boDem = cacKhoi.pop() ?? '';

      for (const khoi of cacKhoi) {
        const suKien = this.phanTichKhoiSse(khoi);
        if (suKien) {
          phatSuKien(suKien);
        }
      }
    }

    const daNgat = controllerSignal.aborted || Boolean(externalSignal?.aborted);
    if (!daNgat && boDem.trim()) {
      const suKienCuoi = this.phanTichKhoiSse(boDem);
      if (suKienCuoi) {
        phatSuKien(suKienCuoi);
      }
    }
  }

  /**
   * Phan tich mot khoi van ban SSE gom cac dong `event:`, `data:` va bo qua `: ping`.
   */
  public phanTichKhoiSse(khoi: string): SuKien | null {
    const cacDong = khoi.split(/\r?\n/);
    let tenSuKien = '';
    const cacDongData: string[] = [];

    for (const dong of cacDong) {
      const dongTrim = dong.trimStart();
      if (dongTrim.startsWith(':')) {
        continue;
      }
      if (dong.startsWith('event:')) {
        tenSuKien = dong.substring(6).trim();
      } else if (dong.startsWith('data:')) {
        cacDongData.push(dong.substring(5).trimStart());
      }
    }

    if (cacDongData.length === 0) {
      return null;
    }

    const duLieuJson = cacDongData.join('\n');
    return this.chuyenDoiSangSuKien(tenSuKien, duLieuJson);
  }

  /**
   * Chuyen doi JSON thanh doi tuong SuKien kieu discriminated union theo ten su kien.
   */
  private chuyenDoiSangSuKien(tenSuKien: string, chuoiJson: string): SuKien | null {
    try {
      const obj = JSON.parse(chuoiJson) as Record<string, unknown>;
      switch (tenSuKien) {
        case 'hang_doi':
          return {
            loai: 'hang_doi',
            vi_tri: Number(obj['vi_tri'] ?? 1),
            uoc_luong_giay:
              typeof obj['uoc_luong_giay'] === 'number' ? obj['uoc_luong_giay'] : null,
          } satisfies SuKienHangDoi;
        case 'bat_dau':
          return {
            loai: 'bat_dau',
            hoi_thoai_id: typeof obj['hoi_thoai_id'] === 'number' ? obj['hoi_thoai_id'] : null,
            nguon: String(obj['nguon'] ?? ''),
            tang: Number(obj['tang'] ?? 0),
            model: String(obj['model'] ?? ''),
            da_cat_ngu_canh: Boolean(obj['da_cat_ngu_canh']),
            so_luot_bi_cat: Number(obj['so_luot_bi_cat'] ?? 0),
          } satisfies SuKienBatDau;
        case 'manh':
          return {
            loai: 'manh',
            noi_dung: String(obj['noi_dung'] ?? ''),
          } satisfies SuKienManh;
        case 'xong':
          return {
            loai: 'xong',
            token_vao: Number(obj['token_vao'] ?? 0),
            token_ra: Number(obj['token_ra'] ?? 0),
            chi_phi_usd: Number(obj['chi_phi_usd'] ?? 0),
            toc_do_tok_s: Number(obj['toc_do_tok_s'] ?? 0),
            do_tre_ms: Number(obj['do_tre_ms'] ?? 0),
            nguon: String(obj['nguon'] ?? ''),
            tang: Number(obj['tang'] ?? 0),
            bac_local: typeof obj['bac_local'] === 'string' ? obj['bac_local'] : null,
            model: String(obj['model'] ?? ''),
            nhan_ai: String(obj['nhan_ai'] ?? ''),
            ma_yeu_cau: typeof obj['ma_yeu_cau'] === 'string' ? obj['ma_yeu_cau'] : undefined,
            ha_cap: typeof obj['ha_cap'] === 'boolean' ? obj['ha_cap'] : undefined,
          } satisfies SuKienXong;
        case 'loi':
          return {
            loai: 'loi',
            ma: String(obj['ma'] ?? 'LOI_KHONG_XAC_DINH'),
            thong_diep: String(obj['thong_diep'] ?? 'Đã xảy ra lỗi khi tạo phản hồi.'),
            ma_yeu_cau: String(obj['ma_yeu_cau'] ?? ''),
            phan_da_nhan: typeof obj['phan_da_nhan'] === 'string' ? obj['phan_da_nhan'] : '',
          } satisfies SuKienLoi;
        default:
          return null;
      }
    } catch {
      return null;
    }
  }

  /**
   * Bóc tách thông tin lỗi từ phản hồi HTTP không phải 200 (401, 429, 503...)
   * và xử lý tiêu đề Retry-After khi gặp mã 429.
   */
  private async xuLyPhanHoiLoi(phanHoi: Response): Promise<SuKienLoi> {
    let thongDiep = `Lỗi máy chủ (${phanHoi.status})`;
    let ma = `HTTP_${phanHoi.status}`;
    let maYeuCau = phanHoi.headers.get('X-Ma-Yeu-Cau') ?? '';
    const retryAfter = phanHoi.headers.get('Retry-After');

    try {
      const loiJson = (await phanHoi.json()) as {
        loi?: { ma?: string; thong_diep?: string; ma_yeu_cau?: string };
        detail?: string;
      };
      if (loiJson?.loi) {
        if (loiJson.loi.thong_diep) thongDiep = loiJson.loi.thong_diep;
        if (loiJson.loi.ma) ma = loiJson.loi.ma;
        if (loiJson.loi.ma_yeu_cau) maYeuCau = loiJson.loi.ma_yeu_cau;
      } else if (typeof loiJson?.detail === 'string') {
        thongDiep = loiJson.detail;
      }
    } catch {
      try {
        const textLoi = await phanHoi.text();
        if (textLoi) thongDiep = textLoi;
      } catch {
        // Giữ thông điệp mặc định
      }
    }

    if (phanHoi.status === 429 && retryAfter) {
      thongDiep = `${thongDiep} (Thử lại sau ${retryAfter} giây)`;
    }

    return {
      loai: 'loi',
      ma,
      thong_diep: thongDiep,
      ma_yeu_cau: maYeuCau,
      phan_da_nhan: '',
    };
  }

  /**
   * Xử lý ngoại lệ phát sinh trong quá trình đọc luồng dữ liệu hoặc hủy luồng.
   */
  private async xuLyNgoaiLe(
    err: unknown,
    daHuy: boolean,
    signalAborted: boolean,
    externalAborted: boolean | undefined,
    reader: ReadableStreamDefaultReader<Uint8Array> | undefined,
    observer: { next: (sk: SuKien) => void; error: (e: unknown) => void; complete: () => void },
  ): Promise<void> {
    const laHuongHuy =
      daHuy ||
      signalAborted ||
      Boolean(externalAborted) ||
      (err instanceof DOMException && err.name === 'AbortError') ||
      (typeof err === 'object' &&
        err !== null &&
        'name' in err &&
        (err as { name: string }).name === 'AbortError');

    if (reader) {
      try {
        await reader.cancel();
      } catch {
        // Bo qua loi dong reader khi da huy
      }
    }

    if (laHuongHuy) {
      observer.complete();
      return;
    }

    const thongDiep = err instanceof Error ? err.message : 'Lỗi kết nối mạng';
    observer.next(this.taoSuKienLoiClient('LOI_KET_NOI', thongDiep));
    observer.complete();
  }

  private taoSuKienLoiClient(ma: string, thongDiep: string): SuKienLoi {
    return {
      loai: 'loi',
      ma,
      thong_diep: thongDiep,
      ma_yeu_cau: '',
      phan_da_nhan: '',
    };
  }
}
