// @ts-ignore
import { Request, Response } from 'express';

export default {
  'POST /api/v1/processes/suicide': (req: Request, res: Response) => {
    res
      .status(200)
      .send({
        code: 92,
        data: null,
        msg: '金土始两治结论采石看存选术物海半我。',
        success: true,
      });
  },
};
