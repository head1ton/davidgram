from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . import models, serializers
from davidgram.notifications import views as notification_views
from davidgram.users import models as user_models
from davidgram.users import serializers as user_serializers

class Images(APIView):

  def get(self, request, format=None):

    user = request.user

    following_users = user.following.all()

    image_list = []

    for following_user in following_users:
      user_images = following_user.images.all()[:2]

      for image in user_images:
        image_list.append(image)

    my_images = user.images.all()

    for image in my_images:

      image_list.append(image)

    image_list = list(set(image_list))

    sorted_list = sorted(image_list, key=lambda image: image.created_at , reverse=True)

    # 이부분에 context를 넣어줌으로써 serializer에서 request에 접근을 할 수 있게됨.
    # 그러면 유저가 이미지에 like를 했을 때 아이콘을 핑크색으로 바꿔주는 작업이 가능해진다.
    serializer = serializers.ImageSerializer(sorted_list, many=True, context={'request': request})

    return Response(serializer.data)

  def post(self, request, format=None):

    user = request.user

    serializer = serializers.InputImageSerializer(data = request.data)

    if serializer.is_valid():

      serializer.save(creator=user)

      return Response(data=serializer.data, status=status.HTTP_200_OK)

    else:
      return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LikeImage(APIView):

  def get(self, request, image_id, format=None):

    likes = models.Like.objects.filter(image__id=image_id)

    like_creators_ids = likes.values('creator_id')

    users = user_models.User.objects.filter(id__in=like_creators_ids)

    serializer = user_serializers.ListUserSerializer(users, many=True, context={"request": request})

    return Response(data=serializer.data, status=status.HTTP_200_OK)

  def post(self, request, image_id, format=None):

    user = request.user

    try:
      found_image = models.Image.objects.get(id=image_id)
    except models.Image.DoesNotExist:
      return Response(status=status.HTTP_404_NOT_FOUND)

    try:
      preexisting_like = models.Like.objects.get(
        creator = user,
        image=found_image
      )
      return Response(status=status.HTTP_304_NOT_MODIFIED)

    except models.Like.DoesNotExist:

      new_like = models.Like.objects.create(
        creator=user,
        image=found_image
      )

      notification_views.create_notification(
        user, found_image.creator, 'like', found_image)

      new_like.save()

      return Response(status=status.HTTP_201_CREATED)


class UnLikeImage(APIView):

  def delete(self, request, image_id, format=None):

    user = request.user

    try:
      found_image = models.Image.objects.get(id=image_id)
    except models.Image.DoesNotExist:
      return Response(status=status.HTTP_404_NOT_FOUND)

    try:
      preexisting_like = models.Like.objects.get(
        creator = user,
        image=found_image
      )
      preexisting_like.delete()

      return Response(status=status.HTTP_204_NO_CONTENT)

    except models.Like.DoesNotExist:
      return Response(status=status.HTTP_304_NOT_MODIFIED)


class CommentOnImage(APIView):

  def post(self, request, image_id, format=None):

    user=request.user

    try:
      found_image = models.Image.objects.get(id=image_id)

    except models.Image.DoesNotExist:
      return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = serializers.CommentSerializer(data=request.data)

    if serializer.is_valid():

      serializer.save(creator=user, image=found_image)

      notification_views.create_notification(
        user, found_image.creator, 'comment', found_image, request.data['message'] )

      return Response(data=serializer.data)

    else:
      return Response(data=serializer.errors, status=status.HTTP_404_NOT_FOUND)

class Comment(APIView):

  def delete(self, request, comment_id, format=None):
    try:
      comment = models.Comment.objects.get(id=comment_id, creator=request.user)
      comment.delete()
      return Response(status=status.HTTP_204_NO_CONTENT)

    except models.Comment.DoesNotExist:
      return Response(status=status.HTTP_404_NOT_FOUND)

class Search(APIView):

  def get(self, request, format=None):

    hashtags = request.query_params.get('hashtags', None)

    # hashtags가 None이면 split이 안되기 때문!
    if hashtags is not None:

      hashtags = hashtags.split(",")

      images = models.Image.objects.filter(tags__name__in=hashtags).distinct()
      # distinct는 두번이상 해쉬태그에 걸리지 않기 위해서 넣는거다.
      # tags__name__in은 nested 구조를 탐색하기 위한 거다. tags중 name이 hashtags를 가지고 있는지?를 봄.

      serializer = serializers.CountImageSerializer(images, many=True)

      return Response(data=serializer.data, status=status.HTTP_200_OK)

    else:

      return Response(status=status.HTTP_400_BAD_REQUEST)

class ModerateComments(APIView):

  def delete(self, request, image_id, comment_id, format=None):

    user = request.user #comment를 moderate하고 싶은 유저.

    # try:
    #   image = models.Image.objects.get(id=image_id, creator=user)
    # except models.Image.DoesNotExist:
    #   return Response(status=status.HTTP_404_NOT_FOUND)
    # 보편적인 방법이지만 좋지는 않다. 아래에 있는 comment모델이 이미 image를 가지고 있기 때문에
    # 이 안에서 해결하는 것이 훨씬 좋은(여러의미로) 방법!

    try:
      comment_to_delete = models.Comment.objects.get(
        id=comment_id, image__id=image_id, image__creator=user)
      comment_to_delete.delete()

    except models.Comment.DoesNotExist:
      return Response(status=status.HTTP_404_NOT_FOUND)

    return Response(status=status.HTTP_204_NO_CONTENT)

class ImageDetail(APIView):

  def find_own_image(self, image_id, user):
    try:
      image = models.Image.objects.get(id=image_id, creator=user)
      return image
    except models.Image.DoesNotExist:
      return None

  def get(self, request, image_id, format=None):

    user = request.user

    try:
      image = models.Image.objects.get(id=image_id)
    except models.Image.DoesNotExist:
      return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = serializers.ImageSerializer(image, context={'request': request})

    return Response(data=serializer.data, status=status.HTTP_200_OK)

  def put(self, request, image_id, format=None):

    user = request.user

    image=self.find_own_image(image_id, user)

    if image is None:
      return Response(status=status.HTTP_400_BAD_REQUEST)

    serializer = serializers.InputImageSerializer(
      image, data=request.data, partial=True)
      #partial=true를 넣으면 세개의 모든 필드들이 채워지지 않아도 된다.

    if serializer.is_valid():
      serializer.save(creator=user)
      return Response(data=serializer.data, status=status.HTTP_204_NO_CONTENT)

    else:
      return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

  def delete(self, request, image_id, format=None):

    user = request.user

    image=self.find_own_image(image_id, user)

    if image is None:
      return Response(status=status.HTTP_400_BAD_REQUEST)

    image.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)