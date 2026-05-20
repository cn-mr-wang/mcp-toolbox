# 数据库备份脚本
# 参数: {db_name}, {output_dir}
mysqldump -u root {db_name} > {output_dir}/{db_name}_$(date +%Y%m%d_%H%M%S).sql
echo "Backup saved to {output_dir}/{db_name}_$(date +%Y%m%d_%H%M%S).sql"
