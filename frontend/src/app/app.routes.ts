import { Routes } from '@angular/router';
import { authGuard, dangNhapGuard } from './core/auth/auth.guard';

/**
 * Moi tuyen duong ung voi dung mot man hinh co chuc nang rieng:
 * - `/dang-nhap`        Man hinh dang nhap cho can bo nhan vien.
 * - `/`                 Trang chu: bang thong tin va loi tat (can xac thuc).
 * - `/tro-chuyen/moi`   Khung tro chuyen trong, san sang nhan cau hoi dau tien (can xac thuc).
 * - `/tro-chuyen/:id`   Khung tro chuyen cua mot hoi thoai da co (can xac thuc).
 * - `/lich-su`          Tra cuu, mo lai va xoa hoi thoai (can xac thuc).
 */
export const routes: Routes = [
  {
    path: 'dang-nhap',
    title: 'Đăng nhập · Trợ lý nội bộ',
    canActivate: [dangNhapGuard],
    loadComponent: () => import('./features/dang-nhap/dang-nhap').then((m) => m.DangNhapComponent),
  },
  {
    path: '',
    pathMatch: 'full',
    title: 'Trang chủ · Trợ lý nội bộ',
    canActivate: [authGuard],
    loadComponent: () => import('./features/trang-chu/trang-chu').then((m) => m.TrangChuComponent),
  },
  { path: 'tro-chuyen', pathMatch: 'full', redirectTo: 'tro-chuyen/moi' },
  { path: 'chat', redirectTo: 'tro-chuyen/moi' },
  {
    path: 'tro-chuyen/:id',
    title: 'Trò chuyện · Trợ lý nội bộ',
    canActivate: [authGuard],
    loadComponent: () => import('./features/chat/chat').then((m) => m.ChatComponent),
  },
  {
    path: 'lich-su',
    title: 'Lịch sử hội thoại · Trợ lý nội bộ',
    canActivate: [authGuard],
    loadComponent: () => import('./features/hoi-thoai/hoi-thoai').then((m) => m.HoiThoaiComponent),
  },
  {
    path: 'quan-tri/bo-chay',
    title: 'Tình trạng bộ chạy · Trợ lý nội bộ',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/quan-tri-bo-chay/quan-tri-bo-chay').then((m) => m.QuanTriBoChayComponent),
  },
  {
    path: 'huong-dan',
    title: 'Hướng dẫn sử dụng · Trợ lý nội bộ',
    canActivate: [authGuard],
    loadComponent: () => import('./features/huong-dan/huong-dan').then((m) => m.HuongDanComponent),
  },
  { path: '**', redirectTo: '' },
];
