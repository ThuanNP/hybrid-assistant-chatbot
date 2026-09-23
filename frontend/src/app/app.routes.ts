import { Routes } from '@angular/router';

/**
 * Moi tuyen duong ung voi dung mot man hinh co chuc nang rieng:
 * - `/`                 Trang chu: bang thong tin va loi tat.
 * - `/tro-chuyen/moi`   Khung tro chuyen trong, san sang nhan cau hoi dau tien.
 * - `/tro-chuyen/:id`   Khung tro chuyen cua mot hoi thoai da co.
 * - `/lich-su`          Tra cuu, mo lai va xoa hoi thoai.
 * Hai tuyen tro chuyen dung chung mot cau hinh `:id` de thanh phan duoc giu nguyen khi
 * hoi thoai moi nhan ma tu may chu, khong ngat luong phat dang chay.
 */
export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    title: 'Trang chủ · Trợ lý nội bộ',
    loadComponent: () => import('./features/trang-chu/trang-chu').then((m) => m.TrangChuComponent),
  },
  { path: 'tro-chuyen', pathMatch: 'full', redirectTo: 'tro-chuyen/moi' },
  { path: 'chat', redirectTo: 'tro-chuyen/moi' },
  {
    path: 'tro-chuyen/:id',
    title: 'Trò chuyện · Trợ lý nội bộ',
    loadComponent: () => import('./features/chat/chat').then((m) => m.ChatComponent),
  },
  {
    path: 'lich-su',
    title: 'Lịch sử hội thoại · Trợ lý nội bộ',
    loadComponent: () => import('./features/hoi-thoai/hoi-thoai').then((m) => m.HoiThoaiComponent),
  },
  { path: '**', redirectTo: '' },
];
