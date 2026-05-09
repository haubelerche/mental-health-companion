
const Loading = ({ text = 'Bạn chờ xíu nha...' }) => {
    return (
        <div className="flex items-center justify-center h-[50dvh]">
            <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-theme-text-secondary mx-auto mb-4"></div>
                <p className="text-theme-text-primary">{text}</p>
            </div>
        </div>
    )
}

export default Loading