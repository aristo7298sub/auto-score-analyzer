/**
 * 格式化文件大小
 * @param bytes 字节数
 * @returns 格式化后的文件大小字符串
 */
export const formatFileSize = (bytes: number | null | undefined): string => {
    if (!bytes || bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
};

/**
 * 格式化日期时间
 * @param isoString ISO格式的日期字符串
 * @returns 格式化后的日期时间字符串
 */
export const formatDateTime = (isoString: string | null | undefined): string => {
    if (!isoString) return '-';

    const date = typeof isoString === 'string' || typeof isoString === 'number'
        ? new Date(isoString as any)
        : new Date(String(isoString));

    if (Number.isNaN(date.getTime())) return '-';

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
};

/**
 * 格式化相对时间（几分钟前、几小时前等）
 * @param isoString ISO格式的日期字符串
 * @returns 格式化后的相对时间字符串
 */
export const formatRelativeTime = (isoString: string | null | undefined): string => {
    return formatRelativeTimeWithLocale(isoString);
};

/**
 * 格式化相对时间（支持中英文）
 * @param isoString ISO格式的日期字符串
 * @param locale 例如 'zh-CN' | 'en-US'。不传则使用浏览器语言（可用时）
 */
export const formatRelativeTimeWithLocale = (
    isoString: string | null | undefined,
    locale?: string,
): string => {
    if (!isoString) return '-';

    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return '-';

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();

    const seconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    const resolvedLocale =
        locale || (typeof navigator !== 'undefined' ? navigator.language : undefined) || 'zh-CN';

    const isZh = resolvedLocale.toLowerCase().startsWith('zh');

    if (typeof Intl !== 'undefined' && typeof Intl.RelativeTimeFormat !== 'undefined') {
        const rtf = new Intl.RelativeTimeFormat(resolvedLocale, { numeric: 'auto' });
        if (seconds < 60) return rtf.format(0, 'second');
        if (minutes < 60) return rtf.format(-minutes, 'minute');
        if (hours < 24) return rtf.format(-hours, 'hour');
        if (days < 7) return rtf.format(-days, 'day');
        return formatDateTime(isoString);
    }

    if (seconds < 60) return isZh ? '刚刚' : 'Just now';
    if (minutes < 60) return isZh ? `${minutes}分钟前` : `${minutes} minutes ago`;
    if (hours < 24) return isZh ? `${hours}小时前` : `${hours} hours ago`;
    if (days < 7) return isZh ? `${days}天前` : `${days} days ago`;

    return formatDateTime(isoString);
};
