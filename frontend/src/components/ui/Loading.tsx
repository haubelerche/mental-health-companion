import loadingImg from '@/assets/motion/loading.gif'
const Loading = ({ text = 'Bạn chờ xíu nha...' }) => {
    return (
        <div className="flex items-center justify-center h-[50dvh]">
            <div className="text-center">
                <img className="mx-auto" src={loadingImg} alt="loading" />
                <p className="text-xl mt-3 text-theme-text-primary font-display font-semibold">{text}</p>
            </div>
        </div>
    )
}

export default Loading