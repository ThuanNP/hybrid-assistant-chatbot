import { Component, input } from '@angular/core';

/**
 * Bo bieu tuong net manh dung chung (24 x 24, stroke 2), mot phong cach duy nhat
 * theo DESIGN.md muc 0.
 */
export type TenBieuTuong =
  | 'trang-chu'
  | 'them'
  | 'tro-chuyen'
  | 'lich-su'
  | 'tim-kiem'
  | 'xoa'
  | 'gui'
  | 'dung'
  | 'sao-chep'
  | 'da-xong'
  | 'menu'
  | 'dong'
  | 'thu-gon'
  | 'mo-rong'
  | 'ho-so'
  | 'but'
  | 'bieu-do'
  | 'tai-lieu'
  | 'mui-ten-phai'
  | 'chip'
  | 'dong-ho'
  | 'canh-bao'
  | 'khien'
  | 'tien'
  | 'hang-doi'
  | 'chuong'
  | 'mui-ten-xuong'
  | 'nguoi-dung'
  | 'lich'
  | 'bo-loc';

@Component({
  selector: 'app-bieu-tuong',
  host: { class: 'bieu-tuong', 'aria-hidden': 'true' },
  styles: `
    :host {
      display: inline-flex;
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }
    svg {
      width: 100%;
      height: 100%;
    }
  `,
  template: `
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      @switch (ten()) {
        @case ('trang-chu') {
          <path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /><path d="M10 21v-6h4v6" />
        }
        @case ('them') {
          <path d="M12 5v14" /><path d="M5 12h14" />
        }
        @case ('tro-chuyen') {
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        }
        @case ('lich-su') {
          <path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 4v5h5" /><path d="M12 7v5l3 2" />
        }
        @case ('tim-kiem') {
          <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
        }
        @case ('xoa') {
          <path d="M3 6h18" /><path d="M8 6V4h8v2" /><path d="M19 6l-1 14H6L5 6" />
        }
        @case ('gui') {
          <path d="M12 19V5" /><path d="m5 12 7-7 7 7" />
        }
        @case ('dung') {
          <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" stroke="none" />
        }
        @case ('sao-chep') {
          <rect x="9" y="9" width="12" height="12" rx="2" />
          <path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1" />
        }
        @case ('da-xong') {
          <path d="M20 6 9 17l-5-5" />
        }
        @case ('menu') {
          <path d="M3 6h18" /><path d="M3 12h18" /><path d="M3 18h18" />
        }
        @case ('dong') {
          <path d="M18 6 6 18" /><path d="m6 6 12 12" />
        }
        @case ('thu-gon') {
          <rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /><path d="m16 10-2 2 2 2" />
        }
        @case ('mo-rong') {
          <rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /><path d="m14 10 2 2-2 2" />
        }
        @case ('ho-so') {
          <path d="M4 4h10l6 6v10H4z" /><path d="M14 4v6h6" /><path d="M8 14h8" /><path d="M8 17h5" />
        }
        @case ('but') {
          <path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />
        }
        @case ('bieu-do') {
          <path d="M3 3v18h18" /><path d="M7 15l4-4 3 3 5-6" />
        }
        @case ('tai-lieu') {
          <path d="M6 3h9l4 4v14H6z" /><path d="M9 11h7" /><path d="M9 15h7" />
        }
        @case ('mui-ten-phai') {
          <path d="m9 18 6-6-6-6" />
        }
        @case ('chip') {
          <rect x="6" y="6" width="12" height="12" rx="2" /><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4" />
        }
        @case ('dong-ho') {
          <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
        }
        @case ('canh-bao') {
          <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
          <path d="M12 9v4" /><path d="M12 17h.01" />
        }
        @case ('khien') {
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        }
        @case ('tien') {
          <circle cx="12" cy="12" r="9" /><path d="M15 9.5c-.6-.9-1.7-1.5-3-1.5-1.7 0-3 .9-3 2s1.3 1.7 3 2 3 .9 3 2-1.3 2-3 2c-1.3 0-2.4-.6-3-1.5" /><path d="M12 6v12" />
        }
        @case ('hang-doi') {
          <path d="M4 6h16" /><path d="M4 12h10" /><path d="M4 18h6" />
        }
        @case ('chuong') {
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0" />
        }
        @case ('mui-ten-xuong') {
          <path d="m6 9 6 6 6-6" />
        }
        @case ('bo-loc') {
          <path d="M4 6h10" /><path d="M18 6h2" /><circle cx="16" cy="6" r="2" />
          <path d="M4 12h4" /><path d="M12 12h8" /><circle cx="10" cy="12" r="2" />
          <path d="M4 18h12" /><circle cx="18" cy="18" r="2" />
        }
        @case ('lich') {
          <rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18" /><path d="M8 3v4M16 3v4" />
        }
        @case ('nguoi-dung') {
          <circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" />
        }
      }
    </svg>
  `,
})
export class BieuTuongComponent {
  public readonly ten = input.required<TenBieuTuong>();
}
