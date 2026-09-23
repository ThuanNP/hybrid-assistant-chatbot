/**
 * cau-hinh.ts - Khai bao cac hang so cau hinh ung dung.
 * Tuan thu quy chuan naming.md: UPPER_SNAKE_CASE cho hang so.
 */

import { environment } from '../../environments/environment';

export const API_GOC = environment.apiGoc;

export const ENDPOINTS = {
  HEALTH: '/health',
  READY: '/ready',
  CHAT_STREAM: `${API_GOC}/chat/stream`,
  CHAT: `${API_GOC}/chat`,
  HOI_THOAI: `${API_GOC}/hoi-thoai`,
  CHI_PHI: `${API_GOC}/chi-phi`,
  MODELS: `${API_GOC}/models`,
  HANG_DOI_TINH_TRANG: `${API_GOC}/hang-doi/tinh-trang`,
  NGU_CANH_TINH_TRANG: `${API_GOC}/ngu-canh/tinh-trang`,
} as const;

export const CAU_HINH_APP = {
  TIEU_DE_HE_THONG: 'Trợ lý nội bộ',
  DON_VI: 'Doanh nghiệp Kinh doanh Điện năng',
  SO_LUOT_TOI_DA_TRANG: 20,
  DO_RONG_SIDEBAR_CHUAN: 240,
  DO_RONG_SIDEBAR_THU_GON: 72,
  NGUONG_MOBILE_PX: 768,
} as const;
