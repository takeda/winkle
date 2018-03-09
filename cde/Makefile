.PHONY: all consul-start consul-stop consul-log haproxy-stop

all:
	@echo "Usage:"
	@echo "make consul-start - starts consul"
	@echo "make consul-stop  - stops consul"
	@echo "make consul-log   - tail log"
	@echo "make haproxy-stop - stops haproxy"

consul-start:
	@echo "Starting consul ..."
	@./service consul_start

consul-stop:
	@echo "Stopping consul ..."
	@./service consul_stop

consul-log:
	@./service consul_log

haproxy-stop:
	@echo "Stopping haproxy ..."
	@./service haproxy_stop
