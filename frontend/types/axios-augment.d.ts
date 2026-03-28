import 'axios';

declare module 'axios' {
  export interface AxiosRequestConfig {
    /** 为 true 时不向 console 打印该次失败的错误（用于轮询等可预期重试） */
    silentErrorLog?: boolean;
  }
}
