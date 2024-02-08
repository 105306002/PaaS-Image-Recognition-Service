
import face_recognition
import boto3
import pickle
import tempfile
import os
import logging
import json
import subprocess
import shlex
from boto3.dynamodb.conditions import Key, Attr


INPUT_BUCKET_NAME = "546proj2inputbucket"
OUTOUT_BUCKET_NAME= "546proj2outputbucket"
SIGNED_URL_TIMEOUT= 5000
s3 = boto3.client('s3', region_name='us-east-1')
dynamodb = boto3.client('dynamodb', region_name='us-east-1')

# Function to read the 'encoding' file
def open_encoding(filename):
	file = open(filename, "rb")
	data = pickle.load(file)
	file.close()
	return data



    
def face_recognition_handler(event, context):	
	try:
		print("face_recognition_handler processing")

		#s3_source_bucket = event['Records'][0]['s3']['bucket']['name']
		s3_source_key = event['Records'][0]['s3']['object']['key']
		#path = "/tmp/"
		s3_source_basename = s3_source_key.split(".")[0] + "-" #extract file name
		dir = tempfile.mkdtemp(prefix = s3_source_basename)
		video_path = dir + "/" + s3_source_basename

		s3.download_file(INPUT_BUCKET_NAME, s3_source_key, video_path)

		#s3_source_signed_url = s3.generate_presigned_url('get_object',Params={'Bucket': s3_source_bucket, 'Key': s3_source_key},ExpiresIn=SIGNED_URL_TIMEOUT)

		os.system("ffmpeg -i " +  str(video_path) + " -r 1 " + str(dir) +  "/" + "image-%3d.jpeg")
		# ffmpeg_cmd = "ffmpeg -i " + str(video_path) + " -vframes 1 " + str(dir) + "/" +"image-%2d.jpeg"
		
		# os.system(ffmpeg_cmd)

		image_files = [f for f in os.listdir(dir) if f.endswith('.jpeg')]
		print('image_files',image_files)
		for image in image_files:
			unknown_known_image = face_recognition.load_image_file(dir + "/" + image)
			face_locations = face_recognition.face_locations(unknown_known_image)
			unknown_image_encoding = face_recognition.face_encodings(unknown_known_image, face_locations)
			print('unknown_image_encoding', unknown_image_encoding)
			script_dir = os.path.dirname(__file__)
			print('script_dir', script_dir)
			encoding_lists = open_encoding(os.path.join(script_dir, "encoding"))
			print('encoding_lists', encoding_lists)

			for face_encoding in unknown_image_encoding:
				results = face_recognition.compare_faces(encoding_lists['encoding'], face_encoding)
				matching_names = [name for i, name in enumerate(encoding_lists['name']) if results[i]][0]
				print('for loop inside', results)
				response = dynamodb.scan(
					TableName='cse546proj2',  
					FilterExpression='#n = :name',
					ExpressionAttributeNames={'#n': 'name'},
					ExpressionAttributeValues={':name': {'S': matching_names}}
				)

				student_info = []
				student_item = response['Items'][0]
				name = student_item['name']['S']
				major = student_item['major']['S']
				year = student_item['year']['S']
				student_info.append([name, major, year])
				csv_content = '\n'.join([','.join(row) for row in student_info])

				s3.put_object(
					Bucket=OUTOUT_BUCKET_NAME,  
					Key=f'{s3_source_key.split(".")[0]}.csv',
					Body=csv_content
				)
	except Exception as e:
		logging.error("Exception occurred", exc_info=True)
	finally:
		return {
			'statusCode': 200,
			'body': 'CSV file generated and uploaded to S3'
		}
    
    
    
    




    # Query the database to search for info

    # Store into the output bucket
    # resp = s3_client.put_object(Body=p1.stdout, Bucket=output_bucket, Key=s3_destination_filename)

    # Return {'statusCode': 200, 'body': json.dumps('Processing complete successfully')}


# if not is_aws_env():


# face_recognition_handler({},{})
	

