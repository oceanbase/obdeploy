// @ts-ignore
import { Request, Response } from 'express';

export default {
  'DELETE /api/v1/deployments/:name': (req: Request, res: Response) => {
    res
      .status(200)
      .send({
        code: 70,
        data: null,
        msg: '被或队他少而置面置般类立严无也最。',
        success: true,
      });
  },
};
