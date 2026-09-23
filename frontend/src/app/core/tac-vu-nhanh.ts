/**
 * tac-vu-nhanh.ts - Danh muc tac vu nhanh dung chung cho Trang chu va man chao cua Tro chuyen
 * (DESIGN.md muc 8.5).
 */

import { TenBieuTuong } from '../shared/bieu-tuong/bieu-tuong';

export interface TacVuNhanh {
  readonly tieuDe: string;
  readonly moTa: string;
  readonly cauHoi: string;
  readonly bieuTuong: TenBieuTuong;
}

export const DANH_SACH_TAC_VU_NHANH: readonly TacVuNhanh[] = [
  {
    tieuDe: 'Tra cứu quy trình',
    moTa: 'Quy trình cấp điện mới cho hộ gia đình',
    cauHoi: 'Tra cứu quy trình cấp điện mới cho hộ gia đình gồm những bước nào?',
    bieuTuong: 'ho-so',
  },
  {
    tieuDe: 'Soạn công văn',
    moTa: 'Công văn trả lời kiến nghị của khách hàng',
    cauHoi: 'Soạn công văn trả lời khách hàng kiến nghị về hoá đơn tiền điện tăng cao.',
    bieuTuong: 'but',
  },
  {
    tieuDe: 'Diễn giải biểu giá',
    moTa: 'Biểu giá bán lẻ điện sinh hoạt bậc thang',
    cauHoi: 'Diễn giải cách tính tiền điện sinh hoạt theo biểu giá bán lẻ bậc thang.',
    bieuTuong: 'bieu-do',
  },
  {
    tieuDe: 'Tóm tắt văn bản',
    moTa: 'Điểm chính của văn bản quy định mới',
    cauHoi: 'Tóm tắt các điểm chính của văn bản quy định mới mà tôi cung cấp sau đây.',
    bieuTuong: 'tai-lieu',
  },
];
