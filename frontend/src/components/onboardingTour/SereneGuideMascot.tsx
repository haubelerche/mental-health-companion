import hauLuong from '../../assets/assistants/hau-luong.png'

type Props = {
    className?: string
}

export default function SereneGuideMascot({ className = '' }: Props) {
    return (
        <img
            src={hauLuong}
            alt="AI"
            className={['object-contain', className].join(' ')}
            decoding="async"
            style={{ imageRendering: 'pixelated' }}
        />
    )
}
