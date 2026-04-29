
const Loading = ({ text = 'Đang tải...' }) => {
    return (
        <div className="flex items-center justify-center h-[50dvh]">
            <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-serene-primary mx-auto mb-4"></div>
                <p className="text-serene-ink">{text}</p>
            </div>
        </div>
    )
}

export default Loading