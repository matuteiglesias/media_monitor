data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "sensing" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_internet_gateway" "sensing" {
  vpc_id = aws_vpc.sensing.id
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.sensing.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index + 1)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.sensing.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.sensing.id
  }
}

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "task" {
  name        = "${local.name}-task"
  description = "No ingress; HTTPS and VPC DNS egress only"
  vpc_id      = aws_vpc.sensing.id

  egress {
    description = "HTTPS feeds and AWS public endpoints"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "VPC resolver UDP"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "VPC resolver TCP"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
}
