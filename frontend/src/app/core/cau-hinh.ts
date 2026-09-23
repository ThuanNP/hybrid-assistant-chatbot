/**
 * cau-hinh.ts - Khai bao cac hang so cau hinh ung dung.
 * Tuan thu quy chuan naming.md: UPPER_SNAKE_CASE cho hang so.
 */

import { environment } from '../../environments/environment';

export const API_GOC = environment.apiGoc;

export const ENDPOINTS = {
  HEALTH: '/health',
  CHAT_STREAM: `${API_GOC}/chat/stream`,
  HOI_THOAI: `${API_GOC}/hoi-thoai`,
  CHI_PHI: `${API_GOC}/chi-phi`,
  MODELS: `${API_GOC}/models`,
  HANG_DOI_TINH_TRANG: `${API_GOC}/hang-doi/tinh-trang`,
} as const;

export const CAU_HINH_APP = {
  TIEU_DE_HE_THONG: 'Trợ lý nội bộ',
  DON_VI: 'Doanh nghiệp Kinh doanh Điện năng',
  /** Tac gia giu ban quyen phan mem, hien o footer. */
  TAC_GIA: 'Nguyễn Phước Thuận',
  NGUONG_MOBILE_PX: 768,
  NGUONG_THU_GON_SIDEBAR_PX: 1100,
} as const;
