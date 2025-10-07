# ################# algoitny Valkey Cluster ###################
# resource "aws_elasticache_replication_group" "algoitny_redis_cluster" {
#   replication_group_id          = "algoitny-cl-${data.terraform_remote_state.vpc.outputs.shard_id}"
#   replication_group_description = "algoitny valkey cluster replica group"

#   # Engine type
#   engine = "valkey"

#   # Change the node type
#   node_type = "cache.t4g.micro"

#   # Change the port you want to use
#   port = 7379

#   # Change the engine version
#   engine_version = "7.2"

#   # Specify the subnet group we created before
#   subnet_group_name = "subnets-${data.terraform_remote_state.vpc.outputs.shard_id}"

#   # Specify the security group for redis elastiscache
#   security_group_ids = [aws_security_group.algoitny_redis.id]

#   # Specify the parameter group for redis elastiscache
#   parameter_group_name       = aws_elasticache_parameter_group.algoitny_redis_cluster_pg.name
#   automatic_failover_enabled = true


#   # Configuration for cluster mode
#   cluster_mode {
#     replicas_per_node_group = 1
#     num_node_groups         = 1
#   }

#   tags = {
#     Name    = "algoitny-redis-cluster"
#     project = "algoitny"
#     role    = "redis"
#     billing = data.terraform_remote_state.vpc.outputs.billing_tag
#     stack   = data.terraform_remote_state.vpc.outputs.vpc_name
#     region  = data.terraform_remote_state.vpc.outputs.aws_region
#   }
# }

# # Route53 Record for elasticache
# resource "aws_route53_record" "algoitny_redis_cluster" {
#   zone_id = data.terraform_remote_state.vpc.outputs.route53_internal_zone_id
#   name    = "algoitny-redis-cluster.${data.terraform_remote_state.vpc.outputs.route53_internal_domain}"
#   type    = "CNAME"
#   ttl     = 300
#   records = [aws_elasticache_replication_group.algoitny_redis_cluster.configuration_endpoint_address]
# }
# ######################################################

