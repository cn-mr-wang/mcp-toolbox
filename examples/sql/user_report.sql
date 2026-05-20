-- 用户统计报表
-- 参数: {start_date}, {end_date}
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS new_users,
    SUM(COUNT(*)) OVER (ORDER BY DATE(created_at)) AS cumulative_users
FROM users
WHERE created_at >= {start_date}
  AND created_at < {end_date}
GROUP BY DATE(created_at)
ORDER BY date;
