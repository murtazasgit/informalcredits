export default function UserInfoBar({ user, score }) {
  if (!user) return null

  const initials = user.user_id.replace('U', '#')

  return (
    <div className="user-info-bar">
      <div className="user-avatar">
        {user.user_id.slice(-2)}
      </div>
      <div className="user-details">
        <div className="user-name">Profile {user.user_id}</div>
        <div className="user-meta">
          <span>Age: {user.age}</span>
          <span>📍 {user.city_tier?.replace('-', ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
          <span>💼 {user.employment_status?.replace(/-/g, ' ')}</span>
          <span>🎓 {user.education_level?.replace(/_/g, ' ')}</span>
          <span>₹{user.monthly_income?.toLocaleString('en-IN')}/mo</span>
        </div>
      </div>
      <div className={`card-badge badge-${score.risk_category.toLowerCase()}`}>
        {score.risk_category}
      </div>
    </div>
  )
}
