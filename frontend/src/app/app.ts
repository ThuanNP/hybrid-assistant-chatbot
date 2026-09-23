import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  imports: [RouterOutlet],
  selector: 'app-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  public readonly tieuDe = signal('Trợ lý nội bộ');
  public readonly tenNguoiDung = signal('Cán bộ Điện lực');
  public readonly phongBan = signal('Kinh doanh Điện năng');
  public readonly sidebarThuGon = signal(false);
  public readonly drawerMo = signal(false);

  public chuyenDoiSidebar(): void {
    if (window.innerWidth < 768) {
      this.drawerMo.update((hienTai) => !hienTai);
      return;
    }
    this.sidebarThuGon.update((hienTai) => !hienTai);
  }

  public dongDrawer(): void {
    this.drawerMo.set(false);
  }
}
