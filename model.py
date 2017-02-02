# Original Version: Taehoon Kim (http://carpedm20.github.io)
#   + Source: https://github.com/carpedm20/DCGAN-tensorflow/blob/e30539fb5e20d5a0fed40935853da97e9e55eee8/model.py
#   + License: MIT
# [2016-08-05] Modifications for Completion: Brandon Amos (http://bamos.github.io)
#   + License: MIT

from __future__ import division
import os
import time
from glob import glob

import numpy as np
import tensorflow as tf
from six.moves import xrange

import ops
import utils

class DCGAN(object):
    def __init__(self, sess, image_size=64, is_crop=False,
                 batch_size=64, sample_size=64,
                 z_dim=100, gf_dim=128, df_dim=64,
                 gfc_dim=1024, dfc_dim=1024, c_dim=1,
                 checkpoint_dir=None, lam=0.1):
        """

        Args:
            sess: TensorFlow session
            batch_size: The size of batch. Should be specified before trainig.
            z_dim: (optional) Dimension of dim for Z. [100]
            gf_dim: (optional) Dimension of gen filters in first conv layer. [64]
            df_dim: (optional) Dimension of discrim filters in first conv layer. [64]
            gfc_dim: (optional) Dimension of gen untis for for fully connected layer. [1024]
            dfc_dim: (optional) Dimension of discrim units for fully connected layer. [1024]
            c_dim: (optional) Dimension of image color. [3]
        """
        self.sess = sess
        self.is_crop = is_crop
        self.batch_size = batch_size
        self.image_size = image_size
        self.sample_size = sample_size
        self.image_shape = [image_size, image_size, c_dim]

        self.imread_mode = 'L' if c_dim == 1 else 'RGB'

        self.z_dim = z_dim

        self.gf_dim = gf_dim
        self.df_dim = df_dim

        self.gfc_dim = gfc_dim
        self.dfc_dim = dfc_dim

        self.lam = lam

        self.c_dim = c_dim

        # batch normalization : deals with poor initialization helps gradient flow
        self.d_bn1 = ops.batch_norm(name='d_bn1')
        self.d_bn2 = ops.batch_norm(name='d_bn2')
        self.d_bn3 = ops.batch_norm(name='d_bn3')

        self.g_bn0 = ops.batch_norm(name='g_bn0')
        self.g_bn1 = ops.batch_norm(name='g_bn1')
        self.g_bn2 = ops.batch_norm(name='g_bn2')
        self.g_bn3 = ops.batch_norm(name='g_bn3')

        self.checkpoint_dir = checkpoint_dir
        self.build_model()

        self.model_name = "DCGAN.model"

    def build_model(self):
        self.images = tf.placeholder(
            tf.float32, [None] + self.image_shape, name='real_images')
        self.sample_images= tf.placeholder(
            tf.float32, [None] + self.image_shape, name='sample_images')
        self.z = tf.placeholder(tf.float32, [None, self.z_dim], name='z')
        self.z_sum = tf.histogram_summary("z", self.z)

        self.G = self.generator(self.z)
        self.D, self.D_logits = self.discriminator(self.images)
        self.D_, self.D_logits_ = self.discriminator(self.G, reuse=True)

        self.sampler = self.sampler(self.z)

        self.d_sum = tf.histogram_summary("d", self.D)
        self.d__sum = tf.histogram_summary("d_", self.D_)
        self.G_sum = tf.image_summary("G", self.G)

        self.d_loss_real = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(self.D_logits,
                                                    tf.ones_like(self.D)))
        self.d_loss_fake = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(self.D_logits_,
                                                    tf.zeros_like(self.D_)))
        self.g_loss = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(self.D_logits_,
                                                    tf.ones_like(self.D_)))

        self.d_loss_real_sum = tf.scalar_summary("d_loss_real", self.d_loss_real)
        self.d_loss_fake_sum = tf.scalar_summary("d_loss_fake", self.d_loss_fake)

        self.d_loss = self.d_loss_real + self.d_loss_fake

        self.g_loss_sum = tf.scalar_summary("g_loss", self.g_loss)
        self.d_loss_sum = tf.scalar_summary("d_loss", self.d_loss)

        t_vars = tf.trainable_variables()

        self.d_vars = [var for var in t_vars if 'd_' in var.name]
        self.g_vars = [var for var in t_vars if 'g_' in var.name]

        self.saver = tf.train.Saver(max_to_keep=1)

    def train(self, config):
        data = glob(os.path.join(config.dataset, '*')
        #np.random.shuffle(data)
        assert(len(data) >= self.batch_size)

        d_optim = tf.train.AdamOptimizer(config.learning_rate, beta1=config.beta1) \
                          .minimize(self.d_loss, var_list=self.d_vars)
        g_optim = tf.train.AdamOptimizer(config.learning_rate, beta1=config.beta1) \
                          .minimize(self.g_loss, var_list=self.g_vars)
        tf.initialize_all_variables().run()

        self.g_sum = tf.merge_summary(
            [self.z_sum, self.d__sum, self.G_sum, self.d_loss_fake_sum, self.g_loss_sum])
        self.d_sum = tf.merge_summary(
            [self.z_sum, self.d_sum, self.d_loss_real_sum, self.d_loss_sum])
        self.writer = tf.train.SummaryWriter("./logs", self.sess.graph)

        sample_z = np.random.uniform(-1, 1, size=(self.sample_size , self.z_dim))
        sample_files = data[0:self.sample_size]
        sample = [utils.get_nifti_image(sample_file, self.image_size) for sample_file in sample_files]
        sample_images = np.array(sample).astype(np.float32)

        counter = 1
        start_time = time.time()

        if self.load(self.checkpoint_dir):
            print("""

======
An existing model was found in the checkpoint directory.
If you just cloned this repository, it's Brandon Amos'
trained model for faces that's used in the post.
If you want to train a new model from scratch,
delete the checkpoint directory or specify a different
--checkpoint_dir argument.
======

""")
        else:
            print("""

======
An existing model was not found in the checkpoint directory.
Initializing a new one.
======

""")

        #for epoch in xrange(config.epoch):
        epoch = 0
        n_samples = 0
        while True:
            batch_idxs = min(len(data), config.train_size) // self.batch_size

            for idx in xrange(0, batch_idxs):
                batch_files = data[idx*config.batch_size:(idx+1)*config.batch_size]
                batch = [utils.get_nifti_image(batch_file, self.image_size)
                         for batch_file in batch_files]
                batch_images = np.array(batch).astype(np.float32)

                batch_z = np.random.uniform(-1, 1, [config.batch_size, self.z_dim]) \
                            .astype(np.float32)

                # Update D network
                _, summary_str = self.sess.run([d_optim, self.d_sum],
                    feed_dict={ self.images: batch_images, self.z: batch_z })
                self.writer.add_summary(summary_str, counter)

                # Update G network
                _, summary_str = self.sess.run([g_optim, self.g_sum],
                    feed_dict={ self.z: batch_z })
                self.writer.add_summary(summary_str, counter)

                # Run g_optim twice to make sure that d_loss does not go to zero (different from paper)
                _, summary_str = self.sess.run([g_optim, self.g_sum],
                    feed_dict={ self.z: batch_z })
                self.writer.add_summary(summary_str, counter)

                errD_fake = self.d_loss_fake.eval({self.z: batch_z})
                errD_real = self.d_loss_real.eval({self.images: batch_images})
                errG = self.g_loss.eval({self.z: batch_z})

                print("Epoch: [%2d] [%4d/%4d] time: %4.4f, d_loss: %.8f, g_loss: %.8f" \
                    % (epoch, idx, batch_idxs,
                        time.time() - start_time, errD_fake+errD_real, errG))

                # if np.mod(counter, 20) == 0:
                if np.power(1.1, n_samples) <= counter:
                    n_samples += 1
                    samples, d_loss, g_loss = self.sess.run(
                        [self.sampler, self.d_loss, self.g_loss],
                        feed_dict={self.z: sample_z, self.images: sample_images}
                    )
                    utils.save_images(samples, [8, 8],
                                './samples/train_{:02d}_{:04d}.png'.format(epoch, idx))
                    print("[Sample] d_loss: %.8f, g_loss: %.8f" % (d_loss, g_loss))

                if np.mod(counter, 100) == 0:
                    self.save(config.checkpoint_dir, counter)
                counter += 1
            epoch += 1

    def complete(self, config):
        os.makedirs(os.path.join(config.outDir, 'hats_imgs'), exist_ok=True)
        os.makedirs(os.path.join(config.outDir, 'completed'), exist_ok=True)

        tf.initialize_all_variables().run()

        isLoaded = self.load(self.checkpoint_dir)
        assert(isLoaded)

        nImgs = len(config.imgs)

        batch_idxs = int(np.ceil(nImgs/self.batch_size))
        if config.maskType == 'random':
            fraction_masked = 0.2
            mask = np.ones(self.image_shape)
            mask[np.random.random(self.image_shape[:2]) < fraction_masked] = 0.0
        elif config.maskType == 'center':
            scale = 0.25
            assert(scale <= 0.5)
            mask = np.ones(self.image_shape)
            sz = self.image_size
            l = int(self.image_size*scale)
            u = int(self.image_size*(1.0-scale))
            mask[l:u, l:u, :] = 0.0
        elif config.maskType == 'left':
            mask = np.ones(self.image_shape)
            c = self.image_size // 2
            mask[:,:c,:] = 0.0
        elif config.maskType == 'full':
            mask = np.ones(self.image_shape)
        else:
            assert(False)

        for idx in xrange(0, batch_idxs):
            l = idx*self.batch_size
            u = min((idx+1)*self.batch_size, nImgs)
            batchSz = u-l
            batch_files = config.imgs[l:u]
            batch = [utils.get_nifti_image(batch_file, self.image_size)
                     for batch_file in batch_files]
            batch_images = np.array(batch).astype(np.float32)
            if batchSz < self.batch_size:
                print(batchSz)
                padSz = ((0, int(self.batch_size-batchSz)), (0,0), (0,0), (0,0))
                batch_images = np.pad(batch_images, padSz, 'constant')
                batch_images = batch_images.astype(np.float32)

            batch_mask = np.resize(mask, [self.batch_size] + self.image_shape)
            zhats = np.random.uniform(-1, 1, size=(self.batch_size, self.z_dim))
            v = 0

            nRows = np.ceil(batchSz/8)
            nCols = 8
            utils.save_images(batch_images[:batchSz,:,:,:], [nRows,nCols],
                        os.path.join(config.outDir, 'before.png'))
            masked_images = np.multiply(batch_images, batch_mask)
            utils.save_images(masked_images[:batchSz,:,:,:], [nRows,nCols],
                        os.path.join(config.outDir, 'masked.png'))

            for i in xrange(config.nIter):
                fd = {
                    self.z: zhats,
                    self.mask: batch_mask,
                    self.images: batch_images,
                }
                run = [self.complete_loss, self.grad_complete_loss, self.G]
                loss, g, G_imgs = self.sess.run(run, feed_dict=fd)

                v_prev = np.copy(v)
                v = config.momentum*v - config.lr*g[0]
                zhats += -config.momentum * v_prev + (1+config.momentum)*v
                zhats = np.clip(zhats, -1, 1)

                if i % 50 == 0:
                    print(i, np.mean(loss[0:batchSz]))
                    imgName = os.path.join(config.outDir,
                                           'hats_imgs/{:04d}.png'.format(i))
                    nRows = np.ceil(batchSz/8)
                    nCols = 8
                    utils.save_images(G_imgs[:batchSz,:,:,:], [nRows,nCols], imgName)

                    inv_masked_hat_images = np.multiply(G_imgs, 1.0-batch_mask)
                    completeed = masked_images + inv_masked_hat_images
                    imgName = os.path.join(config.outDir,
                                           'completed/{:04d}.png'.format(i))
                    utils.save_images(completeed[:batchSz,:,:,:], [nRows,nCols], imgName)
        return counter

    def discriminator(self, image, reuse=False):
        if reuse:
            tf.get_variable_scope().reuse_variables()

        h0 = ops.lrelu(ops.conv2d(image, self.df_dim, name='d_h0_conv'))
        h1 = ops.lrelu(self.d_bn1(ops.conv2d(h0, self.df_dim*2, name='d_h1_conv')))
        h4 = ops.linear(tf.reshape(h1, [-1, 8192]), 1, 'd_h1_lin')

        return tf.nn.sigmoid(h4), h4

    def generator(self, z):
        def define_constant(dividend, divisor):
            # making sure the constants are ints
            quotient = int(dividend / divisor)
            if abs(quotient - dividend / divisor) / 2 > .2:
                raise Exception("Bad dimension. Haven't figured out how or if to deal with this.")
            return quotient

        # some constants to share between generator and sampler
        self.STARTING_GF_DIM = define_constant(self.gf_dim, 2)
        self.STARTING_IMG_DIM = define_constant(self.image_size, 4) # 2^(number of layers - 1)

        self.z_, self.h0_w, self.h0_b=ops.linear(z, self.STARTING_IMG_DIM * self.STARTING_IMG_DIM * self.STARTING_GF_DIM, 'g_h0_lin', with_w=True)

        self.h0 = tf.reshape(self.z_, [-1, self.STARTING_IMG_DIM, self.STARTING_IMG_DIM, self.STARTING_GF_DIM])
        h0 = tf.nn.relu(self.g_bn0(self.h0))

        self.h1, self.h1_w, self.h1_b = ops.conv2d_transpose(h0,
                    [self.batch_size, self.STARTING_IMG_DIM * 2, self.STARTING_IMG_DIM * 2, self.STARTING_GF_DIM * 2], name='g_h1', with_w=True)
        h1 = tf.nn.relu(self.g_bn1(self.h1))

        h4, self.h4_w, self.h4_b = ops.conv2d_transpose(h1,
                    [self.batch_size, self.STARTING_IMG_DIM * 4, self.STARTING_IMG_DIM * 4, self.c_dim], name='g_h4', with_w=True)

        return tf.nn.tanh(h4)

    def sampler(self, z, y=None):
        ''' cannot be called before generator '''
        tf.get_variable_scope().reuse_variables()

        h0 = tf.reshape(ops.linear(z, self.STARTING_IMG_DIM * self.STARTING_IMG_DIM * self.STARTING_GF_DIM, 'g_h0_lin'),
                        [-1, self.STARTING_IMG_DIM, self.STARTING_IMG_DIM, self.STARTING_GF_DIM])
        h0 = tf.nn.relu(self.g_bn0(h0, train=False))

        h1 = ops.conv2d_transpose(h0, [self.batch_size, self.STARTING_IMG_DIM * 2, self.STARTING_IMG_DIM * 2, self.STARTING_GF_DIM * 2], name='g_h1')
        h1 = tf.nn.relu(self.g_bn1(h1, train=False))

        h4 = ops.conv2d_transpose(h1, [self.batch_size, self.STARTING_IMG_DIM * 4, self.STARTING_IMG_DIM * 4, self.c_dim], name='g_h4')

        return tf.nn.tanh(h4)

    def save(self, checkpoint_dir, step):
        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)

        self.saver.save(self.sess,
                        os.path.join(checkpoint_dir, self.model_name),
                        global_step=step)

    def load(self, checkpoint_dir):
        print(" [*] Reading checkpoints...")

        ckpt = tf.train.get_checkpoint_state(checkpoint_dir)
        if ckpt and ckpt.model_checkpoint_path:
            self.saver.restore(self.sess, ckpt.model_checkpoint_path)
            return True
        else:
            return False
