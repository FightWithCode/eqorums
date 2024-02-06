from clients.models import Client
from rest_framework import serializers


class ClientSerializer(serializers.ModelSerializer):
	
	class Meta:
		model = Client
		fields = '__all__'


class SignupClientSerializer(serializers.ModelSerializer):
	
	def validate(self, data):
		return data
	
	# def create(self, validated_data):
	# 	obj = Client.objects.create(**validated_data)
	# 	# update values as required
	# 	# call save method
	# 	obj.save()
	# 	return obj 

	class Meta:
		model = Client
		fields = '__all__'