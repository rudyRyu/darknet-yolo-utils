#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import argparse
import warnings
from PIL import Image


class YOLO_Kmeans:
    def __init__(self, cluster_number, filename, anchors_file, model_image_size):
        self.cluster_number = cluster_number
        self.filename = filename
        self.anchors_file = anchors_file
        self.model_image_size = model_image_size

    def iou(self, boxes, clusters):  # 1 box -> k clusters
        n = boxes.shape[0]
        k = self.cluster_number

        box_area = boxes[:, 0] * boxes[:, 1]
        box_area = box_area.repeat(k)
        box_area = np.reshape(box_area, (n, k))

        cluster_area = clusters[:, 0] * clusters[:, 1]
        cluster_area = np.tile(cluster_area, [1, n])
        cluster_area = np.reshape(cluster_area, (n, k))

        box_w_matrix = np.reshape(boxes[:, 0].repeat(k), (n, k))
        cluster_w_matrix = np.reshape(np.tile(clusters[:, 0], (1, n)), (n, k))
        min_w_matrix = np.minimum(cluster_w_matrix, box_w_matrix)

        box_h_matrix = np.reshape(boxes[:, 1].repeat(k), (n, k))
        cluster_h_matrix = np.reshape(np.tile(clusters[:, 1], (1, n)), (n, k))
        min_h_matrix = np.minimum(cluster_h_matrix, box_h_matrix)
        inter_area = np.multiply(min_w_matrix, min_h_matrix)

        result = inter_area / (box_area + cluster_area - inter_area)
        return result

    def avg_iou(self, boxes, clusters):
        accuracy = np.mean([np.max(self.iou(boxes, clusters), axis=1)])
        return accuracy

    def kmeans(self, boxes, k, dist=np.median):
        box_number = boxes.shape[0]
        distances = np.empty((box_number, k))
        last_nearest = np.zeros((box_number,))
        np.random.seed()
        clusters = boxes[np.random.choice(
            box_number, k, replace=False)]  # init k clusters
        while True:
            distances = 1 - self.iou(boxes, clusters)

            current_nearest = np.argmin(distances, axis=1)
            if (last_nearest == current_nearest).all():
                break  # clusters won't change
            for cluster in range(k):
                clusters[cluster] = dist(  # update clusters
                    boxes[current_nearest == cluster], axis=0)

            last_nearest = current_nearest

        return clusters

    def result2txt(self, data):
        f = open(self.anchors_file, 'w')
        row = np.shape(data)[0]
        for i in range(row):
            if i == 0:
                x_y = "%d,%d" % (data[i][0], data[i][1])
            else:
                x_y = ", %d,%d" % (data[i][0], data[i][1])
            f.write(x_y)
        f.write("\n")
        f.close()

    def txt2boxes(self):
        f = open(self.filename, 'r')
        dataSet = []
        for line in f:
            infos = line.split(" ")
            # get image size
            image = Image.open(infos[0].strip())
            image_width, image_height = image.size
            length = len(infos)
            for i in range(1, length):
                width = int(infos[i].split(",")[2]) - \
                    int(infos[i].split(",")[0])
                height = int(infos[i].split(",")[3]) - \
                    int(infos[i].split(",")[1])

                # rescale box size to model anchor size
                scale = min(float(self.model_image_size[1])/float(image_width), float(self.model_image_size[0])/float(image_height))
                width = round(width * scale)
                height = round(height * scale)
                dataSet.append([width, height])
        result = np.array(dataSet)
        f.close()
        return result

    def txt2boxes(self):
        f = open(self.filename, 'r')
        dataSet = []
        for line in f:
            infos = line.split(" ")
            # get image size
            image = Image.open(infos[0].strip())
            image_width, image_height = image.size
            length = len(infos)
            for i in range(1, length):
                width = int(infos[i].split(",")[2]) - \
                    int(infos[i].split(",")[0])
                height = int(infos[i].split(",")[3]) - \
                    int(infos[i].split(",")[1])

                # rescale box size to model anchor size
                scale = min(float(self.model_image_size[1])/float(image_width), float(self.model_image_size[0])/float(image_height))
                width = round(width * scale)
                height = round(height * scale)
                dataSet.append([width, height])
        result = np.array(dataSet)
        f.close()
        return result

    def txt2clusters(self):
        all_boxes = self.txt2boxes()
        result = self.kmeans(all_boxes, k=self.cluster_number)
        result = result[np.lexsort(result.T[0, None])]
        self.result2txt(result)
        print("K anchors:\n {}".format(result))
        print("Accuracy: {:.2f}%".format(
            self.avg_iou(all_boxes, result) * 100))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Do K-means anchor clustering on selected dataset')
    parser.add_argument('--annotation_file', type=str, required=True,
            help='annotation txt file for ground truth anchors')
    parser.add_argument('--cluster_number', type=int, required=True,
            help='anchor numbers to cluster')
    parser.add_argument('--anchors_file', type=str, required=True,
            help='anchor file to output')
    parser.add_argument('--model_image_size', type=str, required=False,
            help='model image input size as <height>x<width>, default=%(default)s', default='608x608')

    args = parser.parse_args()

    height, width = args.model_image_size.split('x')
    model_image_size = (int(height), int(width))
    assert (model_image_size[0]%32 == 0 and model_image_size[1]%32 == 0), 'model_image_size should be multiples of 32'

    if args.cluster_number != 9 and args.cluster_number != 6 and args.cluster_number != 5:
        warnings.warn('You choose to generate {} anchor clusters, but default YOLO anchor number should 5, 6 or 9'.format(args.cluster_number))

    kmeans = YOLO_Kmeans(args.cluster_number, args.annotation_file, args.anchors_file, model_image_size)
    kmeans.txt2clusters()
