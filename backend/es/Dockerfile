
FROM docker.elastic.co/elasticsearch/elasticsearch:8.19.0
RUN bin/elasticsearch-plugin install --batch analysis-nori

COPY userdict_ko.txt /usr/share/elasticsearch/config/userdict_ko.txt
COPY synonym-set.txt /usr/share/elasticsearch/config/synonym-set.txt