/**
 * sse.service.ts - Dich vu tiep nhan dong su kien Server-Sent Events (SSE) qua POST.
 * Tuan thu clean_code.md, naming.md va type_safety.md.
 */

import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ENDPOINTS } from './cau-hinh';
import {
  SuKienBatDau,
  SuKienHangDoi,
  SuKienLoi,
  SuKienManh,
  SuKienXong,
  YeuCauChat,
} from './mo-hinh';

export type DuLieuSse =
  | { loai: 'hang_doi'; duLieu: SuKienHangDoi }
  | { loai: 'bat_dau'; duLieu: SuKienBatDau }
  | { loai: 'manh'; duLieu: SuKienManh }
  | { loai: 'xong'; duLieu: SuKienXong }
  | { loai: 'loi'; duLieu: SuKienLoi };

@Injectable({
  providedIn: 'root',
})
export class SseService {
  /**
   * Gui yeu cau chat stream bang fetch va nhan dong du lieu text/event-stream.
   */
  public guiTinNhanStream(yeuCau: YeuCauChat): Observable<DuLieuSse> {
    return new Observable<DuLieuSse>((observer) => {
      const controller = new AbortController();

      const xuLyStream = async () => {
        try {
          const phanHoi = await fetch(ENDPOINTS.CHAT_STREAM, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'text/event-stream',
            },
            body: JSON.stringify(yeuCau),
            signal: controller.signal,
          });

          if (!phanHoi.ok) {
            const thongTinLoi = await phanHoi.text();
            observer.error(new Error(`HTTP ${phanHoi.status}: ${thongTinLoi}`));
            return;
          }

          const reader = phanHoi.body?.getReader();
          if (!reader) {
            observer.error(new Error('Khong the khoi tao bo doc stream.'));
            return;
          }

          const decoder = new TextDecoder('utf-8');
          let boDem = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              break;
            }

            boDem += decoder.decode(value, { stream: true });
            const cacDong = boDem.split('\n\n');
            boDem = cacDong.pop() || '';

            for (const khoi of cacDong) {
              this.phanTichKhoiSse(khoi, (duLieu) => observer.next(duLieu));
            }
          }

          observer.complete();
        } catch (err: unknown) {
          if (!controller.signal.aborted) {
            observer.error(err);
          }
        }
      };

      void xuLyStream();

      return () => {
        controller.abort();
      };
    });
  }

  private phanTichKhoiSse(
    khoi: string,
    callback: (duLieu: DuLieuSse) => void
  ): void {
    const cacDong = khoi.split('\n');
    let tenSuKien = 'message';
    let duLieuJson = '';

    for (const dong of cacDong) {
      if (dong.startsWith('event:')) {
        tenSuKien = dong.substring(6).trim();
      } else if (dong.startsWith('data:')) {
        duLieuJson = dong.substring(5).trim();
      }
    }

    if (!duLieuJson) {
      return;
    }

    try {
      const parsed = JSON.parse(duLieuJson) as Record<string, unknown>;
      switch (tenSuKien) {
        case 'hang_doi':
          callback({ loai: 'hang_doi', duLieu: parsed as unknown as SuKienHangDoi });
          break;
        case 'bat_dau':
          callback({ loai: 'bat_dau', duLieu: parsed as unknown as SuKienBatDau });
          break;
        case 'manh':
          callback({ loai: 'manh', duLieu: parsed as unknown as SuKienManh });
          break;
        case 'xong':
          callback({ loai: 'xong', duLieu: parsed as unknown as SuKienXong });
          break;
        case 'loi':
          callback({ loai: 'loi', duLieu: parsed as unknown as SuKienLoi });
          break;
      }
    } catch {
      // Bo qua cac khoi khong phai JSON chuan
    }
  }
}
