//xử lí thời gian thành 1 phút trước, 2 phút trước, ... 1 giờ trước, 2 giờ trước, ... hôm qua, hôm nay, 1 ngày trước, 2 ngày trước...
export function parseTime(timeString: string) {
    const now = new Date()
    const past = new Date(timeString.replace('Z', ''))
    const diff = now.getTime() - past.getTime()
    const minutes = Math.floor(diff / (1000 * 60))
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    if (    minutes < 1) {
        return 'Vừa xong'
    } else if (minutes < 60) {
        return `${minutes} phút trước`
    } else if (hours < 24) {
        return `${hours} giờ trước`
    } else if (days === 1) {
        return 'Hôm qua'
    } else {
        return `${days} ngày trước`
    }
}   