export interface CauHinhMoiTruong {
  production: boolean;
  apiGoc: string;
}

export const environment: CauHinhMoiTruong = {
  production: true,
  apiGoc: '/api/v1',
};
